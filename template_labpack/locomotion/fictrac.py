import subprocess
import signal
import os
import random
import shutil
from time import sleep
import numpy as np

from stimpack.locomotion import LocoManager, LocoClosedLoopManager

FT_FRAME_NUM_IDX = 0
FT_X_IDX = 14
FT_Y_IDX = 15
FT_THETA_IDX = 16
FT_TIMESTAMP_IDX = 21

FICTRAC_HOST = '127.0.0.1'  # The server's hostname or IP address
FICTRAC_PORT = 33334         # The port used by the server
FICTRAC_BIN =    os.path.join(os.path.expanduser("~"), "src/fictrac/bin/fictrac")
FICTRAC_CONFIG = os.path.join(os.path.expanduser("~"), "src/fictrac/config.txt")

class FtManager(LocoManager):
    def __init__(self, ft_bin=FICTRAC_BIN, ft_config=FICTRAC_CONFIG, save_directory=None, start_at_init=True, verbose=False):
        super().__init__(verbose=verbose)
        
        self.ft_bin = ft_bin
        self.ft_config = ft_config
        self.cwd = os.path.join(os.path.expanduser("~"), 'fictrac_temp_data', str(random.randint(0, 2**31)))
        self.save_directory = save_directory

        self.started = False
        self.p = None

        if start_at_init:
            self.start()

    def set_save_directory(self, save_directory):
        self.save_directory = save_directory

    def start(self):
        if self.started:
            print("Fictrac is already running.")
        else:
            os.makedirs(self.cwd, exist_ok=True)
            self.p = subprocess.Popen([self.ft_bin, self.ft_config, "-v","ERR"], cwd=self.cwd, start_new_session=True)
            self.started = True

    def close(self, timeout=5):
        if self.started:
            self.p.send_signal(signal.SIGINT)
            
            try:
                self.p.wait(timeout=timeout)
            except:
                print("Timeout expired for closing Fictrac. Killing process...")
                self.p.kill()
                self.p.terminate()

            self.p = None
            self.started = False

            if self.save_directory is None or self.save_directory=="":
                print("Deleting Fictrac files from preview.")
                shutil.rmtree(self.cwd)
            else:
                print("Moving Fictrac files then deleting.")
                os.makedirs(self.save_directory, exist_ok=True)
                while os.listdir(self.cwd):
                    for fn in os.listdir(self.cwd):
                        shutil.move(os.path.join(self.cwd, fn), self.save_directory)
                shutil.rmtree(self.cwd)

        else:
            print("Fictrac hasn't been started yet. Cannot be closed.")

    def sleep(self, duration):
        sleep(duration)

class FtClosedLoopManager(LocoClosedLoopManager):
    def __init__(self, stim_server, host=FICTRAC_HOST, port=FICTRAC_PORT, save_directory=None, start_at_init=False, udp=True, 
                 ft_bin=FICTRAC_BIN, ft_config=FICTRAC_CONFIG, ft_theta_idx=FT_THETA_IDX, ft_x_idx=FT_X_IDX, ft_y_idx=FT_Y_IDX, ft_frame_num_idx=FT_FRAME_NUM_IDX, ft_timestamp_idx=FT_TIMESTAMP_IDX,
                 ft_ball_diameter=0.009, verbose=False):
        super().__init__(stim_server=stim_server, host=host, port=port, save_directory=save_directory, start_at_init=False, udp=udp, verbose=verbose)

        self.ft_frame_num_idx = ft_frame_num_idx
        self.ft_timestamp_idx = ft_timestamp_idx
        self.ft_theta_idx = ft_theta_idx
        self.ft_x_idx = ft_x_idx
        self.ft_y_idx = ft_y_idx
        self.ft_manager = FtManager(ft_bin=ft_bin, ft_config=ft_config, save_directory=save_directory, start_at_init=False)
        self.ft_ball_diameter = ft_ball_diameter # meters

        self.prev_theta = 0

        if start_at_init:    self.start()

    def set_save_directory(self, save_directory):
        self.save_directory = save_directory
        self.ft_manager.set_save_directory(save_directory)

    def start(self):
        super().start()
        self.ft_manager.start()

    def close(self):
        super().close()
        self.ft_manager.close()

    def _parse_line(self, line):
        toks = line.split(", ")

        # Fictrac lines always starts with FT
        if toks.pop(0) != "FT":
            print('Bad read')
            # Return an empty dict, not None: callers store this as data_prev and take len() of it,
            # so None would raise a TypeError on the next set_pos_0 / update_pos.
            empty_dict: dict[str, float] = {}
            return empty_dict
        
        frame_num = int(toks[self.ft_frame_num_idx])
        ts = float(toks[self.ft_timestamp_idx])

        x = (self.ft_ball_diameter/2) * float(toks[self.ft_x_idx])  # radians -> m
        y = -(self.ft_ball_diameter/2) * float(toks[self.ft_y_idx]) # radians -> m
        theta = -np.rad2deg(float(toks[self.ft_theta_idx]))         # radians -> degrees
        theta = np.unwrap([self.prev_theta, theta], period=360)[1]  # unwrapped
        self.prev_theta = theta
        
        return {'x': x, 'y': y, 'theta': theta, 'frame_num': frame_num, 'ts': ts}
    
