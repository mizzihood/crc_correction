import logging
from logging.handlers import RotatingFileHandler
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml

log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')

logFile = 'C:\\cnc_correction\\cnc.log'
my_handler = RotatingFileHandler(logFile, mode='a', maxBytes=5*1024*1024,
                                 backupCount=10, encoding=None, delay=0)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

logger.addHandler(my_handler)



# The systems have a common origin.
# a is parallel to x.
# The ab plane is in the xy plane.
# The angle between a and b is gamma,
# b and c is alpha,
# and a and c is beta.


class Correction:
    XYZ = ('X', 'Y', 'Z')

    def __init__(self, settings_file="settings.yaml"):
        self.angle_ab = np.pi / 2
        self.angle_ac = np.pi / 2
        self.angle_bc = np.pi / 2

        self.T = np.matrix([[0, 0, 0], [0, 0, 0], [0, 0, 0]])

        self.xyz_upper_limits = np.array([0., 0., 0.])
        self.xyz_upper_limits.shape = (3, 1)

        self.xyz_lower_limits = np.array([0., 0., 0.])
        self.xyz_lower_limits.shape = (3, 1)

        # initialize from default file
        self.cfg = dict()
        self.configure(settings_file)

    def _init_coordinates(self):
        self.xyz_original = np.array([0., 0., 0.])
        self.xyz_original.shape = (3, 1)

        self.xyz_translated = np.array([np.NaN, np.NaN, np.NaN])
        self.xyz_translated.shape = (3, 1)

    def configure(self, file_name=''):
        if file_name != '':
            self._load_parameters(file_name)
        self._parse_parameters()
        self._calculate_matrix()

    def set_parameters(self, parameters):
        for key, value in parameters.items:
            self.cfg[key] = value

    def _load_parameters(self, file_name='settings.yaml'):
        with open(file_name, "r") as stream:
            try:
                self.cfg = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    def _parse_parameters(self):
        # calculate angle_ab by solving the parallelogram
        translation_cfg = self.cfg['translation']
        a = translation_cfg['side_x']
        b = translation_cfg['side_y']
        q = translation_cfg['diagonal_from_x0y0']
        # w is addition to a so the b,a+w|q form a right triangle
        w = (q ** 2 - (a ** 2 + b ** 2)) / (2 * a)
        logger.info(f"--- x,y plane---")
        logger.info(f"nominal move in x direction:     {a:.3f}")
        logger.info(f"nominal move in y direction:     {b:.3f}")
        logger.info(f"diagonal originating in x,y=0:   {q:.3f}")
        logger.info(f"y move projected to x axis:      {w:.3f}")
        self.angle_ab = np.arccos(w / b)
        logger.info(f"angle between x and y:           {math.degrees(self.angle_ab):.3f}")

        # calculate angle_ac and angle_bc
        logger.info(f"--- x,z and y,z plane---")
        h = translation_cfg['height']
        x = translation_cfg['z_to_x']
        logger.info(f"nominal move in z direction:     {h:.3f}")
        logger.info(f"offset on x axis:                {x:.3f}")
        self.angle_ac = np.arctan2(h, x)
        logger.info(f"angle between x and z:           {math.degrees(self.angle_ac):.3f}")
        y = translation_cfg['z_to_y']
        logger.info(f"offset on y axis:                {y:.3f}")
        self.angle_bc = np.arctan2(h, y)
        logger.info(f"angle between y and z:           {math.degrees(self.angle_bc):.3f}")

        limits_cfg = self.cfg['limits']
        self.xyz_upper_limits = np.array(limits_cfg['upper'])
        self.xyz_upper_limits.shape = (3, 1)
        self.xyz_lower_limits = np.array(limits_cfg['lower'])
        self.xyz_lower_limits.shape = (3, 1)

    def _calculate_matrix(self):
        temp_x3 = np.cos(self.angle_ac)
        temp_y3 = (np.cos(self.angle_bc) - temp_x3 * np.cos(self.angle_ab)) / np.sin(self.angle_ab)
        self.T = np.matrix([
            [1, np.cos(self.angle_ab), np.cos(self.angle_ac)],
            [0, np.sin(self.angle_ab), temp_y3],
            [0, 0, np.sqrt(1 - np.power(temp_x3, 2) - np.power(temp_y3, 2))]
        ])
        self.T = np.linalg.inv(self.T)

    def translate(self, point):
        return self.T * point

    def _validate(self, xyz):
        for index in [index for index, value in enumerate(xyz > self.xyz_upper_limits) if value]:
            logger.warning(
                    f"translated axis {self.XYZ[index]} is above upper limit: " +
                    f"{xyz.item(index):.3f} > " +
                    f"{self.xyz_upper_limits.item(index): .3f}"
            )
        for index in [index for index, value in enumerate(xyz < self.xyz_lower_limits) if value]:
            logger.warning(
                    f"translated axis {self.XYZ[index]} is below lower limit: " +
                    f"{xyz.item(index):.3f} < " +
                    f"{self.xyz_lower_limits.item(index): .3f}"
            )

    def _parse_line(self, line):
        logger.debug(f"Line: {line.strip()}")
        tokens = line.split()
        tokens_out = list()
        coordinate_low_index = -1
        for index, token in enumerate(tokens):
            if token[0] in self.XYZ:
                if coordinate_low_index < 0:
                    logger.debug(f"First coordinate position in line: {index}")
                    coordinate_low_index = index
                value = float(token[1:])
                self.xyz_original[self.XYZ.index(token[0])] = value

            else:
                tokens_out.append(token)
        new_xyz_translated = np.round(
            self.translate(self.xyz_original),
            decimals=3
        )
        logger.debug(f"New nominal position: {np.array2string(self.xyz_original.transpose(), precision=3)}")
        logger.debug(f"New transl. position: {np.array2string(new_xyz_translated.transpose(), precision=3)}")
        self._validate(new_xyz_translated)

        if coordinate_low_index >= 0:
            for index, coordinate in enumerate(new_xyz_translated):
                new = new_xyz_translated.item(index)
                old = self.xyz_translated.item(index)
#                if new != old:
                tokens_out.insert(
                    coordinate_low_index,
                    f"{self.XYZ[index]}{new:.3f}"
                )
                coordinate_low_index += 1
            self.xyz_translated = new_xyz_translated

        return ' '.join([token for token in tokens_out])

    def parse_file(self, file_in_path, file_out_path):

        self._init_coordinates()
        with open(file_in_path) as f_in, open(file_out_path, 'w') as f_out:

            now = datetime.now()
            dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
            f_out.write(";Izvorna datoteka   : " + file_in_path  + "\n")
            f_out.write(";Ustvarjena datoteka: " + file_out_path + "\n")
            f_out.write(";Datum obdelave     : " + dt_string     + "\n")

            logger.info(f"Opened source file {file_in_path}, destination file {file_out_path}")
            lines = f_in.readlines()
            for line in lines:
                line_out = self._parse_line(line)
                f_out.write(line_out + '\n')

def run_with_params(file_in_name, file_out_name="", settings_file='settings.yaml'):
    c = Correction()
    if file_out_name == "":
        file_out_name = Path(file_in_name).stem + "_M_"+ Path(file_in_name).suffix;

    c.parse_file(file_in_name, file_out_name)

if __name__ == "__main__":
    args = sys.argv
    # args[0] = current file
    # args[1] = function name
    # args[2:] = function args : (*unpacked)
    if len(args) > 1:
        globals()[args[1]](*args[2:])
