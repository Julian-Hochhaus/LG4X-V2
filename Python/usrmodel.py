import numpy as np
from lmfit.lineshapes import doniach, gaussian, thermal_distribution
import lmfit
from lmfit import Model
from lmfit.models import guess_from_peak
from scipy.signal import convolve as sc_convolve

def dublett(x, amplitude, sigma, gamma, gaussian_sigma, center, soc, height_ratio, fct_coster_kronig):
    """
    Calculates the convolution of a Doniach-Sunjic Dublett with a Gaussian. Thereby, the Gaussian acts as the
    convolution kernel.
    
    Parameters
    ----------
    x: array-like
        Array containing the energy of the spectrum to fit
    amplitude: float
        factor used to scale the calculated convolution to the measured spectrum. This factor is used as the amplitude
        of the Doniach profile.
    sigma: float
        Sigma of the Doniach profile
    gamma: float
        asymmetry factor gamma of the Doniach profile
    gaussian_sigma: float
        sigma of the gaussian profile which is used as the convolution kernel
    center: float
        position of the maximum of the measured spectrum
    soc: float
        distance of the second-highest peak (higher-bound-orbital) of the spectrum in relation to the maximum of the
        spectrum (the lower-bound orbital)
    height_ratio: float
        height ratio of the second-highest peak (higher-bound-orbital) of the spectrum in relation to the maximum of
        the spectrum (the lower-bound orbital)
    fct_coster_kronig: float
        ratio of the lorentzian-sigma of the second-highest peak (higher-bound-orbital) of the spectrum in relation to
        the maximum of the spectrum (the lower-bound orbital)
    Returns
    ---------
    array-type
        convolution of a doniach dublett and a gaussian profile
    """
    conv_temp = fft_convolve(
        doniach(x, amplitude=1, center=center, sigma=sigma, gamma=gamma) + doniach(x, height_ratio, center - soc,
                                                                                   fct_coster_kronig * sigma, gamma),
        1 / (np.sqrt(2 * np.pi) * gaussian_sigma) * gaussian(x, amplitude=1, center=np.mean(x), sigma=gaussian_sigma))
    return amplitude * conv_temp / max(conv_temp)


def singlett(x, amplitude, sigma, gamma, gaussian_sigma, center):
    """
    Calculates the convolution of a Doniach-Sunjic with a Gaussian.
    Thereby, the Gaussian acts as the convolution kernel.
    
    Parameters
    ----------
    x: array-like
        Array containing the energy of the spectrum to fit
    amplitude: float
        factor used to scale the calculated convolution to the measured spectrum. This factor is used as
        the amplitude of the Doniach profile.
    sigma: float
        Sigma of the Doniach profile
    gamma: float
        asymmetry factor gamma of the Doniach profile
    gaussian_sigma: float
        sigma of the gaussian profile which is used as the convolution kernel
    center: float
        position of the maximum of the measured spectrum
    
    Returns
    ---------
    array-type
        convolution of a doniach profile and a gaussian profile
    """
    conv_temp = fft_convolve(doniach(x, amplitude=1, center=center, sigma=sigma, gamma=gamma),
                             1 / (np.sqrt(2 * np.pi) * gaussian_sigma) * gaussian(x, amplitude=1, center=np.mean(x),
                                                                                  sigma=gaussian_sigma))
    return amplitude * conv_temp / max(conv_temp)


kb = 8.6173e-5  # Boltzmann k in eV/K


def fermi_edge(x, amplitude, center, kt, sigma):
    """
    Calculates the convolution of a Thermal Distribution (Fermi-Dirac Distribution) with a Gaussian.
    Thereby, the Gaussian acts as the convolution kernel.
    
    Parameters
    ----------
    x: array-like
        Array containing the energy of the spectrum to fit
    amplitude: float
        factor used to scale the calculated convolution to the measured spectrum. This factor is used
        as the amplitude of the Gaussian Kernel.
    center: float
        position of the step of the fermi edge
    kt: float
        boltzmann constant in eV multiplied with the temperature T in kelvin
        (i.e. for room temperature kt=kb*T=8.6173e-5 eV/K*300K=0.02585 eV)
    sigma: float
        Sigma of the gaussian profile which is used as the convolution kernel
    
    
    
    Returns
    ---------
    array-type
        convolution of a fermi dirac distribution and a gaussian profile
    """
    conv_temp = fft_convolve(thermal_distribution(x, amplitude=1, center=center, kt=kt, form='fermi'),
                             1 / (np.sqrt(2 * np.pi) * sigma) * gaussian(x, amplitude=1, center=np.mean(x),
                                                                         sigma=sigma))
    return amplitude * conv_temp / max(conv_temp)


def convolve(data, kernel):
    """
    Calculates the convolution of a data array with a kernel by using numpy convolve function.
    To suppress edge effects and generate a valid convolution on the full data range, the input dataset is extended
    at the edges.
    
    Parameters
    ----------
    data: array-like
        1D-array containing the data to convolve
    kernel: array-like
        1D-array which defines the kernel used for convolution
    
    Returns
    ---------
    array-type
        convolution of a data array with a kernel array
    
    See Also
    ---------
    numpy.convolve()
    """

    min_num_pts = min(len(data), len(kernel))
    padding = np.ones(min_num_pts)
    padded_data = np.concatenate((padding * data[0], data, padding * data[-1]))
    out = np.convolve(padded_data, kernel, mode='valid')
    n_start_data = int((len(out) - min_num_pts) / 2)
    return (out[n_start_data:])[:min_num_pts]


def fft_convolve(data, kernel):
    """
    Calculates the convolution of a data array with a kernel by using the convolution theorem and thereby
    transforming the time-consuming convolution operation into a multiplication of FFTs.
    For the FFT and inverse FFT, numpy implementation (which is basically the implementation used in scipy)
    of fft and ifft is used.
    To suppress edge effects and generate a valid convolution on the full data range, the input dataset is
    extended at the edges.
    
    Parameters
    ----------
    data: array-like
        1D-array containing the data to convolve
    kernel: array-like
        1D-array which defines the kernel used for convolution
    
    Returns
    ---------
    array-type
        convolution of a data array with a kernel array
    
    See Also
    ---------
    scipy.signal.convolve()
    """
    min_num_pts = min(len(data), len(kernel))
    padding = np.ones(min_num_pts)
    padded_data = np.concatenate((padding * data[0], data, padding * data[-1]))
    out = sc_convolve(padded_data, kernel, mode='valid', method="fft")
    n_start_data = int((len(out) - min_num_pts) / 2)
    return (out[n_start_data:])[:min_num_pts]


class ConvGaussianDoniachSinglett(lmfit.model.Model):
    __doc__ = "Model of a Doniach dublett profile convoluted with a gaussian. " \
              "See also lmfit->lineshape.gaussian and lmfit->lineshape.doniach." + lmfit.models.COMMON_INIT_DOC

    def __init__(self, *args, **kwargs):
        super().__init__(singlett, *args, **kwargs)
        self._set_paramhints_prefix()

    def _set_paramhints_prefix(self):
        self.set_param_hint('amplitude', value=100, min=0)
        self.set_param_hint('sigma', value=0.2, min=0)
        self.set_param_hint('gamma', value=0.02, min=0)
        self.set_param_hint('gaussian_sigma', value=0.2, min=0)
        self.set_param_hint('center', value=100, min=0)
        g_fwhm_expr = '2*{pre:s}gaussian_sigma*1.1774'
        self.set_param_hint('gaussian_fwhm', expr=g_fwhm_expr.format(pre=self.prefix))
        l_fwhm_expr = '{pre:s}sigma*(2+{pre:s}gamma*2.5135+({pre:s}gamma*3.6398)**4)'
        self.set_param_hint('lorentzian_fwhm', expr=l_fwhm_expr.format(pre=self.prefix))
        full_fwhm_expr = ("0.5346*{pre:s}lorentzian_fwhm+" +
                          "sqrt(0.2166*{pre:s}lorentzian_fwhm**2+{pre:s}gaussian_fwhm**2)")
        self.set_param_hint('fwhm', expr=full_fwhm_expr.format(pre=self.prefix))
        h_expr = "{pre:s}amplitude"
        self.set_param_hint('height', expr=h_expr.format(pre=self.prefix))
        area_expr = "{pre:s}fwhm*{pre:s}height"
        self.set_param_hint('area', expr=area_expr.format(pre=self.prefix))

    def guess(self, data, x=None, **kwargs):
        if x is None:
            return
        self.set_param_hint('sigma', max=0.3 * (x[-1] - x[0]))
        self.set_param_hint('gaussian_sigma', max=0.3 * (x[-1] - x[0]))
        doniach_pars = guess_from_peak(Model(doniach), data, x, negative=False)
        gaussian_sigma = (doniach_pars["sigma"].value + x[1] - x[
            0]) / 2  # gaussian lies between sigma and the experimental res. why not?
        doniach_ampl = doniach_pars["amplitude"].value * np.sqrt(
            np.sum(gaussian(x=x, amplitude=1, center=np.mean(x), sigma=gaussian_sigma))) / (
                               2 * np.sqrt(np.sum(x)))  # gives good initial guesses
        params = self.make_params(amplitude=doniach_ampl, sigma=doniach_pars["sigma"].value,
                                  gamma=doniach_pars["gamma"].value, gaussian_sigma=gaussian_sigma,
                                  center=doniach_pars["center"].value)
        return lmfit.models.update_param_vals(params, self.prefix, **kwargs)


class ConvGaussianDoniachDublett(lmfit.model.Model):
    __doc__ = "Model of a Doniach profile convoluted with a gaussian. " \
              "See also lmfit->lineshape.gaussian and lmfit->lineshape.doniach." + lmfit.models.COMMON_INIT_DOC

    def __init__(self, *args, **kwargs):
        super().__init__(dublett, *args, **kwargs)
        self._set_paramhints_prefix()

    def _set_paramhints_prefix(self):
        self.set_param_hint('amplitude', value=100, min=0)
        self.set_param_hint('sigma', value=0.2, min=0)
        self.set_param_hint('gamma', value=0.02, min=0)
        self.set_param_hint('gaussian_sigma', value=0.2, min=0)
        self.set_param_hint('center', value=285)
        self.set_param_hint('soc', value=2.0)
        self.set_param_hint('height_ratio', value=0.75, min=0)
        self.set_param_hint('fct_coster_kronig', value=1, min=0)
        g_fwhm_expr = '2*{pre:s}gaussian_sigma*1.1774'
        self.set_param_hint('gaussian_fwhm', expr=g_fwhm_expr.format(pre=self.prefix))
        l_p1_fwhm_expr = '{pre:s}sigma*(2+{pre:s}gamma*2.5135+({pre:s}gamma*3.6398)**4)'
        l_p2_fwhm_expr = '{pre:s}sigma*(2+{pre:s}gamma*2.5135+({pre:s}gamma*3.6398)**4)*{pre:s}fct_coster_kronig'
        self.set_param_hint('lorentzian_fwhm_p1', expr=l_p1_fwhm_expr.format(pre=self.prefix))
        self.set_param_hint('lorentzian_fwhm_p2', expr=l_p2_fwhm_expr.format(pre=self.prefix))
        fwhm_p1_expr = ("0.5346*{pre:s}lorentzian_fwhm_p1+" +
                        "sqrt(0.2166*{pre:s}lorentzian_fwhm_p1**2+{pre:s}gaussian_fwhm**2)")
        self.set_param_hint('fwhm_p1', expr=fwhm_p1_expr.format(pre=self.prefix))
        fwhm_p2_expr = ("0.5346*{pre:s}lorentzian_fwhm_p2+" +
                        "sqrt(0.2166*{pre:s}lorentzian_fwhm_p2**2+{pre:s}gaussian_fwhm**2)")
        self.set_param_hint('fwhm_p2', expr=fwhm_p2_expr.format(pre=self.prefix))
        h_p1_expr = "{pre:s}amplitude"
        h_p2_expr = "{pre:s}amplitude*{pre:s}height_ratio"
        self.set_param_hint('height_p1', expr=h_p1_expr.format(pre=self.prefix))
        self.set_param_hint('height_p2', expr=h_p2_expr.format(pre=self.prefix))
        area_p1_expr = "{pre:s}fwhm_p1*{pre:s}height_p1"
        self.set_param_hint('area_p1', expr=area_p1_expr.format(pre=self.prefix))
        area_p2_expr = "{pre:s}fwhm_p2*{pre:s}height_p2"
        self.set_param_hint('area_p2', expr=area_p2_expr.format(pre=self.prefix))

    def guess(self, data, x=None, **kwargs):
        if x is None:
            return
        doniach_pars = guess_from_peak(Model(doniach), data, x, negative=False)
        gaussian_sigma = (doniach_pars["sigma"].value + x[1] - x[
            0]) / 2  # gaussian lies between sigma and the experimental res. why not?
        doniach_ampl = doniach_pars["amplitude"].value * np.sqrt(
            np.sum(gaussian(x=x, amplitude=1, center=np.mean(x), sigma=gaussian_sigma))) / (
                               5 * np.sqrt(np.sum(x)))  # gives good initial guesses
        soc_guess = 0.3 * (
                x[-1] - x[0])  # assuming a highres spectrum, maybe one could implement a solution with peak-find?
        params = self.make_params(amplitude=doniach_ampl, sigma=doniach_pars["sigma"].value / 5,
                                  gamma=doniach_pars["gamma"].value, gaussian_sigma=gaussian_sigma / 5,
                                  center=doniach_pars["center"].value, soc=soc_guess, height_ratio=1)
        return lmfit.models.update_param_vals(params, self.prefix, **kwargs)


class FermiEdgeModel(lmfit.model.Model):
    __doc__ = "Model of a ThermalDistribution convoluted with a gaussian. " \
              "See also lmfit->lineshape.gaussian and lmfit->lineshape.thermal_distribution." \
              + lmfit.models.COMMON_INIT_DOC

    def __init__(self, *args, **kwargs):
        super().__init__(fermi_edge, *args, **kwargs)
        # limit several input parameters to positive values
        self._set_paramhints_prefix()

    def _set_paramhints_prefix(self):
        self.set_param_hint('kt', value=0.02585, min=0)  # initial value is room temperature
        self.set_param_hint('sigma', value=0.2, min=0)
        self.set_param_hint('center', value=100, min=0)
        self.set_param_hint('amplitude', value=100, min=0)

    def guess(self, data, x=None, **kwargs):
        if x is None:
            return
        self.set_param_hint('center', value=np.mean(x), min=min(x), max=max(x))
        self.set_param_hint('kt', value=kb * 300, min=0, max=kb * 1500)
        self.set_param_hint('amplitude', value=(max(data) - min(data)) / 10, min=0, max=(max(data) - min(data)))
        self.set_param_hint('sigma', value=(max(x) - min(x)) / len(x), min=0, max=2)
        params = self.make_params()
        return lmfit.models.update_param_vals(params, self.prefix, **kwargs)


bgrnd = [[], [], []]


def tougaard(x, y, B, C, C_d, D, extend=30, only_vary_B=True):
    """
    Calculates the Tougaard background of an X-ray photoelectron spectroscopy (XPS) spectrum.

    The following implementation is based on the four-parameter loss function (4-PIESCS) as suggested by R.Hesse (
    https://doi.org/10.1002/sia.3746). In contrast to R.Hesse, the Tougaard background is not leveled with the data
    using a constant, but the background on the high-energy side is extended. This approach was found to lead to
    great convergence empirically, however, the length of the data extension remains arbitrary.

    To reduce computing time, as long as only B should be variate (which makes sense in most cases), if the loss
    function was already calculated, only B is further optimized.

    The 2-PIESCS loss function is created by using C_d=1 and D=0. Using C_d=-1 and D!=0 leads to the 3-PIESCS loss
    function.

    For further details on the 2-PIESCS loss function, see https://doi.org/10.1016/0038-1098(87)90166-9, and for the
    3-PIESCS loss function, see https://doi.org/10.1002/(SICI)1096-9918(199703)25:3<137::AID-SIA230>3.0.CO;2-L

    Parameters
    ----------
    x : array-like
        1D-array containing the x-values (energies) of the spectrum.
    y : array-like
        1D-array containing the y-values (intensities) of the spectrum.
    B : float
        B parameter of the 4-PIESCS loss function as introduced by R.Hesse (https://doi.org/10.1002/sia.3746).
        Acts as scaling factor of the Tougaard background model.
    C : float
        C parameter of the 4-PIESCS loss function as introduced by R.Hesse (https://doi.org/10.1002/sia.3746).
    C_d : float
        C' parameter of the 4-PIESCS loss function as introduced by R.Hesse (https://doi.org/10.1002/sia.3746).
        Set to 1 for the 2-PIESCS loss function. (and D to 0). Set to -1 for the 3-PIESCS loss function (D!=0).
    D : float
        D parameter of the 4-PIESCS loss function as introduced by R.Hesse (https://doi.org/10.1002/sia.3746).
        Set to 0 for the 2-PIESCS loss function (and C_d to 1). Set to !=0 for the 3-PIESCS loss function (C_d=-1).
    extend : float, optional
        Length of the data extension on the high-kinetic-energy side. Defaults to 30.
    only_vary_B : bool, optional
        Whether to only vary the scaling factor `B` when calculating the background. Defaults to True.
        Varying all parameters of Tougaard background leads to instabilities and weird shaped backgrounds.

    Returns
    -------
    array-like
        The Tougaard background of the XPS spectrum.

    See Also ------- The following implementation is based on the four-parameter loss function as suggested by
    R.Hesse [https://doi.org/10.1002/sia.3746].
    """
    global bgrnd
    if np.array_equal(bgrnd[0], y) and only_vary_B and bgrnd[2][0] == extend:
        # check if loss function was already calculated
        return [B * elem for elem in bgrnd[1]]
    else:
        bgrnd[0] = y
        bgrnd[2] = [extend]
        bg = []
        delta_x = abs((x[-1] - x[0]) / len(x))
        len_padded = int(extend / delta_x)  # sets expansion length, values between 15 and 50 work great
        padded_x = np.concatenate((x, np.linspace(x[-1] + delta_x, x[-1] + delta_x * len_padded, len_padded)))
        padded_y = np.concatenate((y, np.mean(y[-10:]) * np.ones(len_padded)))
        for k in range(len(x)):
            x_k = x[k]
            bg_temp = 0
            for j in range(len(padded_y[k:])):
                padded_x_kj = padded_x[k + j]
                bg_temp += (padded_x_kj - x_k) / ((C + C_d * (padded_x_kj - x_k) ** 2) ** 2
                                                  + D * (padded_x_kj - x_k) ** 2) * padded_y[k + j] * delta_x
            bg.append(bg_temp)
        bgrnd[1] = bg
        return np.asarray([B * elem for elem in bgrnd[1]])


class TougaardBG(lmfit.model.Model):
    __doc__ = """
    Model of the 4 parameter loss function Tougaard.

    The implementation is based on the four-parameter loss function (4-PIESCS) as suggested by R.Hesse [
    https://doi.org/10.1002/sia.3746]. In addition, the extend parameter is introduced, which improves the agreement
    between data and Tougaard BG by extending the data on the high-kinetic energy side (low binding energy side) by
    the mean intensity value at the rightmost kinetic energy scale. extend represents the length of the data
    extension on the high-kinetic-energy side in eV. Defaults to 30.

    Attributes:
        All attributes are inherited from the lmfit.model.Model class.

    Methods:
        __init__(*args, **kwargs):
            Initializes the TougaardBG model instance. Calls the super().__init__() method of the parent class
            (lmfit.model.Model) and sets parameter hints using _set_paramhints_prefix() method.

        _set_paramhints_prefix():
            Sets parameter hints for the model. Sets initial values and constraints for the parameters 'B', 'C',
            'C_d', 'D', and 'extend'.

        guess(data, x=None, **kwargs):
            Generates initial parameter values for the model based on the provided data and optional arguments.

    Note:
        The TougaardBG class inherits from lmfit.model.Model and extends it with specific behavior and functionality
        related to the Tougaard 4 parameter loss function.
    """ + lmfit.models.COMMON_INIT_DOC

    def __init__(self, *args, **kwargs):
        """
        Initializes the TougaardBG model instance.

        """
        super().__init__(tougaard, *args, **kwargs)
        self._set_paramhints_prefix()

    def _set_paramhints_prefix(self):
        """
        Sets parameter hints for the model.

        The method sets initial values and constraints for the parameters 'B', 'C', 'C_d', 'D', and 'extend'.

        """
        self.set_param_hint('B', value=2886, min=0)
        self.set_param_hint('C', value=1643, min=0)
        self.set_param_hint('C_d', value=1, min=0)
        self.set_param_hint('D', value=1, min=0)
        self.set_param_hint('extend', value=30, vary=False)

    def guess(self, data, x=None, **kwargs):
        """
        Generates initial parameter values for the model based on the provided data and optional arguments.

        Parameters:
            data (array-like): Array containing the data (=intensities) to fit.
            x (array-like): Array containing the independent variable values.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Parameters: Initial parameter values for the model.

        Note:
            The method requires the 'x' parameter to be provided.
        """
        if x is None:
            return
        params = self.make_params(B=2886, C=1643, C_d=1, D=1)
        return lmfit.models.update_param_vals(params, self.prefix, **kwargs)


def shirley(y, k, const):
    """
    Calculates the Shirley background of an X-ray photoelectron spectroscopy (XPS) spectrum.
    This implementation calculates the Shirley background by integrating the step characteristic of the spectrum.

    Parameters
    ----------
    y : array-like
        1D-array containing the y-values (intensities) of the spectrum.
    k : float
        Slope of the step characteristic.
    const : float
        Constant offset of the step characteristic.

    Returns
    -------
    array-like
        The Shirley background of the XPS spectrum.
    """
    n = len(y)
    y_right = const
    y_temp = y - y_right  # step characteristic is better approximated if only the step without background is integrated
    bg = []
    for i in range(n):
        bg.append(np.sum(y_temp[i:]))
    return np.asarray([k * elem + y_right for elem in bg])


class ShirleyBG(lmfit.model.Model):
    __doc__ = """
    Model of the Shirley background for X-ray photoelectron spectroscopy (XPS) spectra. 

    Attributes:
        All attributes are inherited from the lmfit.model.Model class.

    Methods:
        __init__(*args, **kwargs):
            Initializes the ShirleyBG model instance. Calls the super().__init__() method of the parent class
            (lmfit.model.Model) and sets parameter hints using _set_paramhints_prefix() method.

        _set_paramhints_prefix():
            Sets parameter hints for the model. Sets initial values and constraints for the parameters 'k' and 'const'.

        guess(data, x=None, **kwargs):
            Generates initial parameter values for the model based on the provided data and optional arguments.

    Note:
        The ShirleyBG class inherits from lmfit.model.Model and extends it with specific behavior and functionality
        related to the Shirley background for XPS spectra.
    """ + lmfit.models.COMMON_INIT_DOC

    def __init__(self, *args, **kwargs):
        """
        Initializes the ShirleyBG model instance.

        """
        super().__init__(shirley, *args, **kwargs)
        self._set_paramhints_prefix()

    def _set_paramhints_prefix(self):
        """
        Sets parameter hints for the model.

        The method sets initial values and constraints for the parameters 'k' and 'const'.

        """
        self.set_param_hint('k', value=0.03, min=0)
        self.set_param_hint('const', value=1000, min=0)

    def guess(self, data, x=None, **kwargs):
        """
        Generates initial parameter values for the model based on the provided data and optional arguments.

        Parameters:
            data (array-like): Array containing the data to fit.
            x (array-like): Array containing the independent variable values.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Parameters: Initial parameter values for the model.

        Note:
            The method requires the 'x' parameter to be provided.
        """
        if x is None:
            return
        params = self.make_params(k=0.03, const=1000)
        return lmfit.models.update_param_vals(params, self.prefix, **kwargs)


def slope(y, k):
    """
    Calculates the slope background of an X-ray photoelectron spectroscopy (XPS) spectrum.
    The slope background has some similarities to the Shirley background, e.g. the slope background is calculated
    by integrating the Shirley background from each data point to the end.
    Afterwards, a slope parameter k is used to scale the slope accordingly to the measured data.

    Parameters
    ----------
    y : array-like
        1D-array containing the y-values (intensities) of the spectrum.
    k : float
        Slope of the linear function for determining the background.

    Returns
    -------
    array-like
        The slope background of the XPS spectrum.

    See Also
    --------
    Slope Background implemented as suggested by A. Herrera-Gomez et al in [DOI: 10.1016/j.elspec.2013.07.006].
    """
    n = len(y)
    y_right = np.min(y)
    y_temp = y - y_right
    temp = []
    bg = []
    for i in range(n):
        temp.append(np.sum(y_temp[i:]))
    for j in range(n):
        bg.append(np.sum(temp[j:]))
    return np.asarray([-k * elem for elem in bg])


class SlopeBG(lmfit.model.Model):
    __doc__ = """
    Model of the Slope background for X-ray photoelectron spectroscopy (XPS) spectra.
    Slope Background implemented as suggested by A. Herrera-Gomez et al in [DOI: 10.1016/j.elspec.2013.07.006].

    Attributes:
        All attributes are inherited from the lmfit.model.Model class.

    Methods:
        __init__(*args, **kwargs):
            Initializes the SlopeBG model instance. Calls the super().__init__() method of the parent class
            (lmfit.model.Model) and sets parameter hints using _set_paramhints_prefix() method.

        _set_paramhints_prefix():
            Sets parameter hints for the model. Sets an initial value for the parameter 'k'.

        guess(data, x=None, **kwargs):
            Generates initial parameter values for the model based on the provided data and optional arguments.

    Note:
        The SlopeBG class inherits from lmfit.model.Model and extends it with specific behavior and functionality
        related to the Slope background for XPS spectra.
    """ + lmfit.models.COMMON_INIT_DOC

    def __init__(self, *args, **kwargs):
        """
        Initializes the SlopeBG model instance.
        """
        super().__init__(slope, *args, **kwargs)
        self._set_paramhints_prefix()

    def _set_paramhints_prefix(self):
        """
        Sets parameter hints for the model.

        The method sets an initial value for the parameter 'k'.

        """
        self.set_param_hint('k', value=0.01)

    def guess(self, data, x=None, **kwargs):
        """
        Generates initial parameter values for the model based on the provided data and optional arguments.

        Parameters:
            data (array-like): Array containing the data to fit.
            x (array-like): Array containing the independent variable values.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Parameters: Initial parameter values for the model.

        Note:
            The method requires the 'x' parameter to be provided.
        """
        if x is None:
            return
        params = self.make_params(k=0.01)
        return lmfit.models.update_param_vals(params, self.prefix, **kwargs)
