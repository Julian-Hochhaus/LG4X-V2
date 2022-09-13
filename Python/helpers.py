from lmfit.models import ExponentialGaussianModel, SkewedGaussianModel, SkewedVoigtModel, DoniachModel, \
    BreitWignerModel, LognormalModel
from lmfit.models import GaussianModel, LorentzianModel, VoigtModel, PseudoVoigtModel, ThermalDistributionModel, \
    PolynomialModel, StepModel
from usrmodel import ConvGaussianDoniachDublett, ConvGaussianDoniachSinglett, FermiEdgeModel, singlett, fft_convolve
def autoscale_y(ax, margin=0.1):
    """This function rescales the y-axis based on the data that is visible given the current xlim of the axis.
    ax -- a matplotlib axes object
    margin -- the fraction of the total height of the y-data to pad the upper ylims"""

    import numpy as np

    def get_bottom_top(line):
        xd = line.get_xdata()
        yd = line.get_ydata()
        lo, hi = ax.get_xlim()
        if not np.max(yd) == np.min(yd):
            y_displayed = yd[((xd > lo) & (xd < hi))]
            h = np.max(y_displayed) - np.min(y_displayed)
            if np.min(y_displayed) - 2 * margin * (np.max(y_displayed) - np.min(y_displayed)) > 0:
                bot = np.min(y_displayed) - 2 * margin * (np.max(y_displayed) - np.min(y_displayed))
            else:
                bot = 0
            top = np.max(y_displayed) + margin * h
        else:
            bot, top = np.min(yd), np.max(yd)
        return bot, top

    lines = ax.get_lines()
    bot, top = np.inf, -np.inf

    for line in lines:
        new_bot, new_top = get_bottom_top(line)
        if new_bot < bot:
            bot = new_bot
        if new_top > top:
            top = new_top

    ax.set_ylim(bot, top)



def modelSelector(index, strind, index_pk):
    if index == 0:
        pk_mod = GaussianModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 1:
        pk_mod = LorentzianModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 2:
        pk_mod = VoigtModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 3:
        pk_mod = PseudoVoigtModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 4:
        pk_mod = ExponentialGaussianModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 5:
        pk_mod = SkewedGaussianModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 6:
        pk_mod = SkewedVoigtModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 7:
        pk_mod = BreitWignerModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 8:
        pk_mod = LognormalModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 9:
        pk_mod = DoniachModel(prefix=strind + str(index_pk + 1) + '_')
    if index == 10:
        pk_mod = ConvGaussianDoniachDublett(prefix=strind + str(index_pk + 1) + '_')
    if index == 11:
        pk_mod = ConvGaussianDoniachSinglett(prefix=strind + str(index_pk + 1) + '_')
    if index == 12:
        pk_mod = FermiEdgeModel(prefix=strind + str(index_pk + 1) + '_')

    return pk_mod

