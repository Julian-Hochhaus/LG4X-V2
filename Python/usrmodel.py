import matplotlib.pyplot as plt
import numpy as np
from lmfit.lineshapes import doniach, gaussian, thermal_distribution 
import lmfit
from lmfit import  Model
from lmfit.models import guess_from_peak
def dublett(x, amplitude,sigma,gamma, gaussian_sigma, center , soc, height_ratio, factor_sigma_doniach):
    """
    Calculates the convolution of a Doniach-Sunjic Dublett with a Gaussian. Thereby, the Gaussian acts as the convolution kernel.
    
    Parameters
    ----------
    x: array:
        Array containing the energy of the spectrum to fit
    amplitude: float
        factor used to scale the calculated convolution to the measured spectrum. This factor is used as the amplitude of the Doniach profile.
    sigma: float
        Sigma of the Doniach profile
    gamma: float
        asymmetry factor gamma of the Doniach profile
    gaussian_sigma: float
        sigma of the gaussian profile which is used as the convolution kernel
    center: float
        position of the maximum of the measured spectrum
    soc: float
        distance of the second-highest peak (higher-binded-orbital) of the spectrum in relation to the maximum of the spectrum (the lower-binded orbital)
    height_ratio: float
        height ratio of the second-highest peak (higher-binded-orbital) of the spectrum in relation to the maximum of the spectrum (the lower-binded orbital)
    factor_sigma_doniach: float
        ratio of the lorentzian-sigma of the second-highest peak (higher-binded-orbital) of the spectrum in relation to the maximum of the spectrum (the lower-binded orbital)   
    Returns
    ---------
    array-type
        convolution of a doniach dublett and a gaussian profile
    """
    return convolve(doniach(x, amplitude, center, sigma, gamma)+doniach(x, height_ratio*amplitude, center-soc, factor_sigma_doniach*sigma, gamma),gaussian(x,amplitude=1,center=np.mean(x),sigma=gaussian_sigma))


def singlett(x,amplitude, sigma, gamma, gaussian_sigma, center):
    """
    Calculates the convolution of a Doniach-Sunjic with a Gaussian. Thereby, the Gaussian acts as the convolution kernel.
    
    Parameters
    ----------
    x: array:
        Array containing the energy of the spectrum to fit
    amplitude: float
        factor used to scale the calculated convolution to the measured spectrum. This factor is used as the amplitude of the Doniach profile.
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
    return convolve(doniach(x, amplitude, center, sigma, gamma),gaussian(x,amplitude=1,center=np.mean(x),sigma=gaussian_sigma))
kb = 8.6173e-5 # Boltzmann k in eV/K
def fermi_edge(x, amplitude,center,kt,sigma):
    """
    Calculates the convolution of a Thermal Distribution (Fermi-Dirac Distribution) with a Gaussian. Thereby, the Gaussian acts as the convolution kernel.
    
    Parameters
    ----------
    x: array:
        Array containing the energy of the spectrum to fit
    amplitude: float
        factor used to scale the calculated convolution to the measured spectrum. This factor is used as the amplitude of the Gaussian Kernel.
    center: float
        position of the step of the fermi edge
    kt: float
        boltzmann konstant in eV multiplied with the temperature T in kelvin (i.e. for room temperature kt=kb*T=8.6173e-5 eV/K*300K=0.02585 eV)
    sigma: float
        Sigma of the gaussian profile which is used as the convolution kernel
    
    
    
    Returns
    ---------
    array-type
        convolution of a fermi direac distribution and a gaussian profile
    """
    return convolve(thermal_distribution(x,amplitude=1,center=center,kt=kt,form='fermi'),gaussian(x,amplitude=amplitude,center=np.mean(x),sigma=sigma))
def convolve(data, kernel):
    """
    Calculates the convolution of an data array with a kernel by using numpy's convolve funtion. 
    To surpress edge effects and generate a valid convolution on the full data range, the input dataset is extended at the edges.
    
    Parameters
    ----------
    data: array:
        1D-array containing the data to convolve
    kernel: array
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
    padded_data = np.concatenate((padding*data[0], data, padding*data[-1]))
    out = np.convolve(padded_data, kernel, mode='valid')
    n_start_data = int((len(out) - min_num_pts) / 2)
    return (out[n_start_data:])[:min_num_pts]

def fft_convolve(data, kernel):
    """
    Calculates the convolution of an data array with a kernel by using the convolution theorem and thereby transforming the time consuming convolution operation into a multiplication of FFTs.
    For the FFT and inverse FFT, numpy's implementation (which is basically the implementation used in scipy) of fft and ifft is used.
    To surpress edge effects and generate a valid convolution on the full data range, the input dataset is extended at the edges.
    
    Parameters
    ----------
    data: array:
        1D-array containing the data to convolve
    kernel: array
        1D-array which defines the kernel used for convolution
    
    Returns
    ---------
    array-type
        convolution of a data array with a kernel array
    
    See Also
    ---------
    numpy.fft.fft()
    numpy.fft.ifft()
    scipy.fft
    """
    min_num_pts = min(len(data), len(kernel))
    padding = np.ones(min_num_pts)
    padded_data = np.concatenate((padding*data[0], data, padding*data[-1]))
    fft_kernel, fft_padded_data=np.fft.fft(kernel), np.fft.fft(padded_data)
    res=np.fft.ifft(fft_kernel*np.fft.fft(data))
    n_start_data = int((len(res) - min_num_pts) / 2)
    return (res[n_start_data:])[:min_num_pts]

    
class ConvGaussianDoniachSinglett(lmfit.model.Model):
    __doc__ = "Model of a Doniach dublett profile convoluted with a gaussian. See also lmfit->lineshape.gaussian and lmfit->lineshape.doniach." + lmfit.models.COMMON_INIT_DOC
    
    def __init__(self, *args, **kwargs):
        super().__init__(singlett, *args, **kwargs)
        #limit several input parameters to positive values
        self.set_param_hint('amplitude', min=0)
        self.set_param_hint('sigma', min=0)
        self.set_param_hint('gaussian_sigma', min=0)
        self.set_param_hint('gamma', min=0) 
        self._set_paramhints_prefix()
    def _set_paramhints_prefix(self):
        self.set_param_hint('amplitude', value=100)
        self.set_param_hint('sigma', value=0.2)
        self.set_param_hint('gaussian_sigma', value=0.2)
        self.set_param_hint('gamma', value=0.02) 
    def guess(self, data, x=None, **kwargs):
        if x is None:
            return
        self.set_param_hint('sigma', max=0.3*(x[-1]-x[0]))
        self.set_param_hint('gaussian_sigma', max=0.3*(x[-1]-x[0]))
        doniach_pars=guess_from_peak(Model(doniach),data,x,negative=False)
        gaussian_sigma=(doniach_pars["sigma"].value+x[1]-x[0])/2 #gaussian lies between sigma and the experimental res. why not?
        doniach_ampl=doniach_pars["amplitude"].value*np.sqrt(np.sum(gaussian(x=x,amplitude=1,center=np.mean(x), sigma=gaussian_sigma)))/(2*np.sqrt(np.sum(x))) #gives good initial guesses
        params = self.make_params(amplitude=doniach_ampl, sigma=doniach_pars["sigma"].value, gamma=doniach_pars["gamma"].value, gaussian_sigma=gaussian_sigma, center=doniach_pars["center"].value)
        return lmfit.models.update_param_vals(params, self.prefix, **kwargs)
    
class ConvGaussianDoniachDublett(lmfit.model.Model):
    __doc__ = "Model of a Doniach profile convoluted with a gaussian. See also lmfit->lineshape.gaussian and lmfit->lineshape.doniach." + lmfit.models.COMMON_INIT_DOC
    
    def __init__(self, *args, **kwargs):
        super().__init__(dublett, *args, **kwargs)
        #limit several input parameters to positive values
        self.set_param_hint('amplitude', min=0)
        self.set_param_hint('sigma', min=0)
        self.set_param_hint('gaussian_sigma', min=0)
        self.set_param_hint('gamma', min=0) 
        self.set_param_hint('height_ratio', min=0)
        self._set_paramhints_prefix()
    def _set_paramhints_prefix(self):
        self.set_param_hint('amplitude', value=100)
        self.set_param_hint('sigma', value=0.2)
        self.set_param_hint('gaussian_sigma', value=0.2)
        self.set_param_hint('gamma', value=0.02) 
        self.set_param_hint('height_ratio', value=0.75)
        self.set_param_hint('soc', value=2)
    def guess(self, data, x=None, **kwargs):
        if x is None:
            return
        doniach_pars=guess_from_peak(Model(doniach),data,x,negative=False)
        gaussian_sigma=(doniach_pars["sigma"].value+x[1]-x[0])/2 #gaussian lies between sigma and the experimental res. why not?
        doniach_ampl=doniach_pars["amplitude"].value*np.sqrt(np.sum(gaussian(x=x,amplitude=1,center=np.mean(x), sigma=gaussian_sigma)))/(5*np.sqrt(np.sum(x))) #gives good initial guesses
        soc_guess=0.3*(x[-1]-x[0])# assuming a highres spectrum, maybe one could implement a solution with peakfind?
        params = self.make_params(amplitude=doniach_ampl, sigma=doniach_pars["sigma"].value/5, gamma=doniach_pars["gamma"].value, gaussian_sigma=gaussian_sigma/5, center=doniach_pars["center"].value, soc=soc_guess,height_ratio=1)
        return lmfit.models.update_param_vals(params, self.prefix, **kwargs)

class FermiEdgeModel(lmfit.model.Model):
    __doc__ = "Model of a ThermalDistribution convoluted with a gaussian. See also lmfit->lineshape.gaussian and lmfit->lineshape.thermal_distribution." + lmfit.models.COMMON_INIT_DOC
    
    def __init__(self, *args, **kwargs):
        super().__init__(fermi_edge, *args, **kwargs)
        #limit several input parameters to positive values
        self.set_param_hint('amplitude', min=0)
        self.set_param_hint('kt', min=0)
        self.set_param_hint('sigma', min=0)
        self._set_paramhints_prefix()
    def _set_paramhints_prefix(self):
        self.set_param_hint('kt', value=0.02585)#initial value is room temperature
        self.set_param_hint('sigma', value=0.2)
    def guess(self, data, x=None, **kwargs):
        if x is None:
            return
        self.set_param_hint('center',value=np.mean(x), min=min(x),max=max(x))
        self.set_param_hint('kt',value=kb*300, min=0,max=kb*1500)
        self.set_param_hint('amplitude',value=(max(data)-min(data))/10, min=0,max=(max(data)-min(data)))
        self.set_param_hint('sigma',value=(max(x)-min(x))/len(x), min=0,max=2)
        params = self.make_params()
        print(params)
        return lmfit.models.update_param_vals(params, self.prefix, **kwargs)