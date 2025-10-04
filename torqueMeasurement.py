import numpy as np
import matplotlib.pyplot as plt
import filedialpy as fd
from scipy.signal import medfilt
from scipy.interpolate import interp1d


class TorqueMeasurement:

    def __init__(self):
        # File selection dialog
        filepath = fd.openFile()
        if not filepath:
            raise ValueError("No file selected.")

        # Load data (skip 10 header lines like MATLAB importdata)
        headers = []
        with open(filepath) as myFile:
            for num, line in enumerate(myFile, 1):
                if 'Timestamp' in line:
                    i = num
                    headers = line.strip().split('\t')
                    break
        data=np.loadtxt(filepath, delimiter='\t',skiprows=i)

        # Expected headers
        standard_headers = [
            "XXX_",
            "Field_",
            "XXX_T_",
            "HtrPwr_",
            "Voltmeter_",
            "Lockin_V_",
            "Timestamp"
        ]

        semiStandard_headers = [
            "Field_001",
            "loadCell_001",
            "temperature_001",
            "angle_001",
            "pickupCoil_001",
            "Timestamp_001"
        ]

        # Check if headers match expected
        standard = all(std in h for std, h in zip(standard_headers, headers))
        semiStandard = all(std in h for std, h in zip(semiStandard_headers, headers))
        
        if standard:
            self.angle = 2.7 * data[:, 0] / 360
            self.field = data[:, 1]
            self.temperature = data[:, 2]
            self.heaterpower = data[:, 3]
            self.pickupcoil = 2.7 * data[:, 4] / 360
            self.loadcell = data[:, 5]
            self.time = data[:, 6]
        elif semiStandard:
            self.temperature = data[:, 2]
            self.time = data[:, 5]
            self.field = data[:, 0]
            self.loadcell = data[:, 1]
            self.pickupcoil = 2.7 * data[:, 4] / 360
            self.heaterpower = data[:, 2]
            self.angle = 2.7 * data[:, 3] / 360
        else:
            print("Headers found:")
            print(headers)
            self.temperature = data[:, int(input("Which column is temperature? [#] > ")) - 1]
            self.time = data[:, int(input("Which column is time? [#] > ")) - 1]
            self.field = data[:, int(input("Which column is magnetic field? [#] > ")) - 1]
            self.loadcell = data[:, int(input("Which column is lock-in voltage (load cell)? [#] > ")) - 1]
            self.pickupcoil = 2.7 * data[:, int(input("Which column is keithley voltage (pickup coil)? [#] > ")) - 1] / 360
            self.heaterpower = data[:, int(input("Which column is heater power? [#] > ")) - 1]
            self.angle = 2.7 * data[:, int(input("Which column is angle? [#] > ")) - 1] / 360
        

        # Ask for sample dimensions
        self.width = 4e-3   #float(input("What is the width of your sample? [m] > "))
        self.length = 13e-3 #float(input("What is the length of your sample? [m] > "))

        # Probe selection
        probe = 1   #int(input("Which probe did you use? (1 or 2) > "))
        if probe == 1:
            self.coeff = 5.4059
        elif probe == 2:
            self.coeff = 5.1669
        else:
            raise ValueError("Invalid probe selection.")
        
        idx = np.where(np.diff(self.angle) <0)[0][0]
        self.rightCutoff = idx

        fig,ax = plt.subplots()
        plt.scatter(np.arange(1, idx), self.loadcell[1:idx])
        plt.title("Load vs Time")
        plt.ylabel("Load [V]")
        plt.xlabel("Index [#]")

        selected = []
        def onclick(event):
            if event.inaxes != ax:
                return
            x, y = event.xdata, event.ydata
            idx = int(round(x))
            selected.append(idx)
            ax.axvline(idx, color="red", linestyle="--")
            fig.canvas.draw()

            if len(selected) == 2:
                fig.canvas.mpl_disconnect(cid)
                left, right = sorted(selected)
                self.leftCutoff = left
                self.rightCutoff = right
                plt.close()

        cid = fig.canvas.mpl_connect("button_press_event", onclick)
        plt.show()   # this returns immediately in widget backend
        
        # Wait for the user to finish selection before proceeding
        while not hasattr(self, 'leftCutoff') or not hasattr(self, 'rightCutoff'):
            plt.pause(0.1)

    def __del__(self):
        pass

    def calcIc(obj):
        cleanAngle = obj.angle[obj.leftCutoff:obj.rightCutoff]
        cleanLoad = obj.loadcell[obj.leftCutoff:obj.rightCutoff]
        cleanField = obj.field[obj.leftCutoff:obj.rightCutoff]
        badSpots = np.where(np.diff(cleanAngle) == 0)[0]
        cleanAngle = np.delete(cleanAngle, badSpots)
        cleanLoad = np.delete(cleanLoad, badSpots)
        cleanField = np.delete(cleanField, badSpots)
        cleanLoad = medfilt(cleanLoad, kernel_size=1)
        rezFit = np.polyfit([cleanAngle[0], cleanAngle[-1]], [cleanLoad[0], cleanLoad[-1]], 1)
        slope = rezFit[0]
        intercept = rezFit[1]
        holder = slope * cleanAngle + intercept
        cleanLoad = cleanLoad - holder
        offset = cleanAngle[np.argmax(cleanLoad)]
        cleanAngle = cleanAngle - offset
        offset = np.min(cleanLoad)
        cleanLoad = cleanLoad - offset
        x = cleanAngle
        g = interp1d(cleanAngle, cleanLoad, bounds_error=False, fill_value="extrapolate")
        ic = (obj.coeff * 4 * 1.3) / (100 * obj.width * obj.length * (1 - (obj.width / (3 * obj.length))))
        ic2 = ic * g(x)
        ic2 = ic2 / (np.mean(cleanField) * np.cos(np.deg2rad(x)))
        result = {}
        result_angle = cleanAngle[(cleanAngle > -30) & (cleanAngle < 30)]
        result['angle'] = np.linspace(np.min(result_angle), np.max(result_angle), len(result_angle))
        z = interp1d(cleanAngle, ic2 * 1000, bounds_error=False, fill_value="extrapolate")
        result['ic'] = z(result['angle'])
    
        return result