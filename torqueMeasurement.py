import numpy as np
import matplotlib.pyplot as plt
import filedialpy as fd
from scipy.signal import medfilt
from scipy.interpolate import interp1d
from scipy.optimize import curve_fit
Colors = ['b', 'r', 'g', 'c', 'm', 'y', 'k']

def doubleLorentz(params, x):
        a, b, c, d = params['i01'], params['gamma1'], params['i02'], params['gamma2']
        cos_x = np.cos(np.radians(x))
        sin_x = np.sin(np.radians(x))
        term1 = (a * b / np.pi) / (cos_x**2 + (b**2) * sin_x**2)
        term2 = (c * d / np.pi) / (cos_x**2 + (d**2) * sin_x**2)
        return term1 + term2

def singleLorentz(params, x):
    i0, gamma = params['i0'], params['gamma']
    cos_x = np.cos(np.radians(x))
    sin_x = np.sin(np.radians(x))
    return (i0 * gamma / np.pi) / (cos_x**2 + (gamma**2) * sin_x**2)

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
    
    def icAngleFit(obj, bool2Plot):
        def fit_func(x, a, b, c, d):
            cos_x = np.cos(np.radians(x))
            sin_x = np.sin(np.radians(x))
            term1 = (a * b / np.pi) / (cos_x**2 + (b**2) * sin_x**2)
            term2 = (c * d / np.pi) / (cos_x**2 + (d**2) * sin_x**2)
            return term1 + term2
        temp = obj.calcIc()
        x= temp['angle']
        y= temp['ic']
        these = (x > -20) & (x < 20)
        x = x[these]
        y = y[these]

        # Initial guess and bounds
        p0 = [1, 3, 1, 12]
        lower_bounds = [0, 1, 0, 1]
        upper_bounds = [np.inf, 5, np.inf, 15]

        # Fit model to data
        i0sGammas, _ = curve_fit(fit_func, x, y, p0=p0, bounds=(lower_bounds, upper_bounds), method='trf', max_nfev=1000)

        if bool2Plot:
            angles = np.arange(-20, 20.1, 0.1)
            temp2 = {'i01': i0sGammas[0], 'gamma1': i0sGammas[1], 'i02': i0sGammas[2], 'gamma2': i0sGammas[3]}
            ics = doubleLorentz(temp2, angles)
            plt.scatter(temp['angle'], temp['ic'], c='black', label='_nolegend_', s=20)
            plt.xlim([-20, 20])
            plt.plot(angles, ics, color='red', linewidth=2)
            plt.xlabel(r'Angle $\left[°\right]$', fontsize=25)
            plt.ylabel(r'$I_{c}$ $\left[A\right]$', fontsize=25)
            plt.grid(True)
            plt.title(r'$I_c(\theta) = \frac{I_1\Gamma_{1}}{cos^2(\theta{}) + \Gamma{}_{1}^{2}sin^2(\theta{})} + \frac{I_2\Gamma_{2}}{cos^2(\theta{}) + \Gamma{}_{2}^{2}sin^2(\theta{})}$', fontsize=25)
            plt.gca().tick_params(labelsize=25)
            plt.text(-15, 0.8 * np.max(temp['ic']), f'$I_1$ = {i0sGammas[0]:.2f} A\n$\\Gamma_1$ = {i0sGammas[1]:.2f}\n$I_2$ = {i0sGammas[2]:.2f} A\n$\\Gamma_2$ = {i0sGammas[3]:.2f}', fontsize=20, bbox=dict(facecolor='white', alpha=0.5))
            plt.show()

        return i0sGammas