import sys

import numpy as np
import yaml
import logging
import math

logging.basicConfig(
    filename='cnc.log',
    level=logging.DEBUG,
    filemode='w',
    format='%(asctime)s\t%(name)s\t%(levelname)s\t%(message)s'
)


# The systems have a common origin.
# a is parallel to x.
# The ab plane is in the xy plane.
# The angle between a and b is gamma,
# b and c is alpha,
# and a and c is beta.


class Correction:
    XYZ = ('X', 'Y', 'Z')

    def __init__(self):
        self.angle_ab = np.pi / 2
        self.angle_ac = np.pi / 2
        self.angle_bc = np.pi / 2

        self.T = np.matrix([[0, 0, 0], [0, 0, 0], [0, 0, 0]])

        self.xyz_original = np.array([0., 0., 0.])
        self.xyz_original.shape = (3, 1)

        self.xyz_transformed = np.array([0., 0., 0.])
        self.xyz_transformed.shape = (3, 1)

        self.new_xyz_transformed = np.array([0., 0., 0.])
        self.new_xyz_transformed.shape = (3, 1)
        # initialize from default file
        self.cfg = dict()
        self.configure('settings.yaml')

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
        a = self.cfg['side_x']
        b = self.cfg['side_y']
        q = self.cfg['diagonal_from_x0y0']
        # w is addition to a so the b,a+w|q form a right triangle
        w = (q ** 2 - (a ** 2 + b ** 2)) / (2 * a)
        logging.info(f"--- x,y plane---")
        logging.info(f"nominal move in x direction:     {a:.3f}")
        logging.info(f"nominal move in y direction:     {b:.3f}")
        logging.info(f"diagonal originating in x,y=0:   {q:.3f}")
        logging.info(f"y move projected to x axis:      {w:.3f}")
        self.angle_ab = np.arccos(w / b)
        logging.info(f"angle between x and y:           {math.degrees(self.angle_ab):.3f}")

        # calculate angle_ac and angle_bc
        logging.info(f"--- x,z and y,z plane---")
        h = self.cfg['height']
        x = self.cfg['z_to_x']
        logging.info(f"nominal move in z direction:     {h:.3f}")
        logging.info(f"offset on x axis:                {x:.3f}")
        self.angle_ac = np.arctan2(h, x)
        logging.info(f"angle between x and z:           {math.degrees(self.angle_ac):.3f}")
        y = self.cfg['z_to_y']
        logging.info(f"offset on y axis:                {y:.3f}")
        self.angle_bc = np.arctan2(h, y)
        logging.info(f"angle between y and z:           {math.degrees(self.angle_bc):.3f}")

    def _calculate_matrix(self):
        temp_x3 = np.cos(self.angle_ac)
        temp_y3 = (np.cos(self.angle_bc) - temp_x3 * np.cos(self.angle_ab)) / np.sin(self.angle_ab)
        self.T = np.matrix([
            [1, np.cos(self.angle_ab), np.cos(self.angle_ac)],
            [0, np.sin(self.angle_ab), temp_y3],
            [0, 0, np.sqrt(1 - np.power(temp_x3, 2) - np.power(temp_y3, 2))]
        ])
        self.T = np.linalg.inv(self.T)

    def transform(self, point):
        return self.T * point

    def _parse_line(self, line):
        tokens = line.split()
        tokens_out = list()
        coordinate_low_index = -1
        for index, token in enumerate(tokens):
            if token[0] in self.XYZ:
                if coordinate_low_index < 0:
                    coordinate_low_index = index

                value = float(token[1:])
                self.xyz_original[self.XYZ.index(token[0])] = value
            else:
                tokens_out.append(token)
        new_xyz_transformed = np.round(
            self.transform(self.xyz_original),
            decimals=3
        )
        self.new_xyz_transformed = new_xyz_transformed
        if coordinate_low_index >= 0:
            for index, coordinate in enumerate(new_xyz_transformed):
                new = new_xyz_transformed.item(index)
                old = self.xyz_transformed.item(index)
                if new != old:
                    tokens_out.insert(
                        coordinate_low_index,
                        f"{self.XYZ[index]}{new:.3f}"
                    )
                    coordinate_low_index += 1
            self.xyz_transformed = new_xyz_transformed

        print(tokens_out)

        return ' '.join([token for token in tokens_out])

    def parse_file(self, file_in_path, file_out_path):
        with open(file_in_path) as f_in, open(file_out_path, 'w') as f_out:
            lines = f_in.readlines()
            for line in lines:
                line_out = self._parse_line(line)
                f_out.write(line_out + '\n')
                print(line_out)


def print_fn():
    print("Hia")


def run_with_params(file_in_name, file_out_name):
    print(file_in_name + file_out_name)
    c = Correction()
    c.parse_file(file_in_name, file_out_name)


if __name__ == "__main__":
    args = sys.argv
    # args[0] = current file
    # args[1] = function name
    # args[2:] = function args : (*unpacked)

    globals()[args[1]](*args[2:])
