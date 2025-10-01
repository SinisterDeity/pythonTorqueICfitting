import numpy as np
import matplotlib.pyplot as plt
import filedialpy as fd


class TorqueMeasurement:
    """
    Container for data generated from Jan Jaroszynski's torque magnetometer
    utilizing NML DAQ at NHMFL.

    Parses the text file generated from the DAQ program and allows calculation
    of Ic by requesting user parameters and cleaning/scaling the data.
    """

    def __init__(self):
        # File selection dialog
        filepath = fd.openFile()
        if not filepath:
            raise ValueError("No file selected.")

        # Load data (skip 10 header lines like MATLAB importdata)
        headerLine = 0
        headers = []
        with open(filepath) as myFile:
            for num, line in enumerate(myFile, 1):
                if 'Timestamp' in line:
                    i = num
                    headers = line.strip().split('\t')
                    break
        data=np.loadtxt(filepath, delimiter='\t',skiprows=headerLine)

        # Expected headers
        standard_headers = [
            "XXX_",
            "Field_",
            "XXX_T_",
            "HtrPwr_",
            "Voltmeter_",
            "Lockin_V_",
            "Timestamp",
        ]

        # Check if headers match expected
        standard = all(std in h for std, h in zip(standard_headers, headers))
        print(standard)
        '''
        if not standard:
            print("Headers found:")
            print(headers)

            self.temperature = data[:, int(input("Which column is temperature? [#] > ")) - 1]
            self.time = data[:, int(input("Which column is time? [#] > ")) - 1]
            self.field = data[:, int(input("Which column is magnetic field? [#] > ")) - 1]
            self.loadcell = data[:, int(input("Which column is lock-in voltage (load cell)? [#] > ")) - 1]
            self.pickupcoil = 2.7 * data[:, int(input("Which column is keithley voltage (pickup coil)? [#] > ")) - 1] / 360
            self.heaterpower = data[:, int(input("Which column is heater power? [#] > ")) - 1]
            self.angle = 2.7 * data[:, int(input("Which column is angle? [#] > ")) - 1] / 360
        else:
            self.angle = 2.7 * data[:, 0] / 360
            self.field = data[:, 1]
            self.temperature = data[:, 2]
            self.heaterpower = data[:, 3]
            self.pickupcoil = 2.7 * data[:, 4] / 360
            self.loadcell = data[:, 5]
            self.time = data[:, 6]

        # Ask for sample dimensions
        self.width = float(input("What is the width of your sample? [m] > "))
        self.length = float(input("What is the length of your sample? [m] > "))

        # Probe selection
        probe = int(input("Which probe did you use? (1 or 2) > "))
        if probe == 1:
            self.coeff = 5.4059
        elif probe == 2:
            self.coeff = 5.1669
        else:
            raise ValueError("Invalid probe selection.")

        # First plot: Load vs Angle
        plt.figure()
        plt.title("Load vs Time")
        plt.ylabel("Load [V]")
        plt.xlabel("Angle [°]")
        plt.scatter(self.angle, self.loadcell)
        plt.show(block=False)
        plt.pause(1)

        # Ask where rotation reverses
        cutoff_angle = float(input("At what angle does the rotation reverse? > "))
        idx = np.argmax(self.angle > cutoff_angle)
        self.rightCutoff = idx
        plt.close()

        # Second plot: Load vs Index
        plt.figure()
        plt.title("Load vs Time")
        plt.ylabel("Load [V]")
        plt.xlabel("Index [#]")
        cutLoad = self.loadcell[:idx]
        plt.scatter(np.arange(len(cutLoad)), cutLoad)
        plt.show(block=False)
        plt.pause(1)

        self.leftCutoff = int(input("Where is the leftmost minima? > "))
        plt.axvline(self.leftCutoff, color="r")

        self.rightCutoff = int(input("Where is the rightmost minima? > "))
        plt.axvline(self.rightCutoff, color="g")

        plt.show(block=True)
        plt.close()
'''
    def __del__(self):
        # Destructor for TorqueMeasurement
        # No explicit resource management needed, but can be used for cleanup
        pass