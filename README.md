<p align="center">
  <a href="https://doi.org/10.5281/zenodo.7777422"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.7777422.svg" alt="DOI"></a>
   <a href="#"><img src="https://img.shields.io/badge/python-3.8%20|%203.9%20|%203.10%20|%203.11%20-blue?logo=python" alt="Python Versions"></a>
  <a href="https://opensource.org/licenses/"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License: MIT"></a>
  <a href="https://en.wikipedia.org/wiki/Free_and_open-source_software"><img src="https://img.shields.io/badge/FOSS-100%25-green.svg?style=flat" alt="FOSS: 100%"></a>
 <img alt="Flathub Downloads" src="https://img.shields.io/flathub/downloads/io.github.julian_hochhaus.LG4X_V2">

</p>

## Hint:
Please use a released version for the productive use of the software (i.e. the latest Release) as they are tested for several different use cases and not the newest Commit, as the different branches are used to work on new and not extensively tested features. The newest commits on the master branch might as well contain bugs as the software is work in progress.

## Announcement:

An advanced version of open-source XPS fitting software is available from [binary](https://sourceforge.net/projects/khervefitting/) and [github](https://github.com/KherveFitting/KherveFitting) developed by Gwilherm Kerherve. The software uses a very similar approach to LG4X/LG4X-V2, combining an even more user-friendly GUI with the models and optimization algorithms implemented in LMFIT/lmfitxps. Please check it out!


## Introduction
 LG4X-V2 is an open-source GUI for X-ray photoemission spectroscopy (XPS) curve fitting based on the python lmfit package. It streamlines the fitting process for easier validation and consistency. It is inspired by its predecessor software [LG4X](https://github.com/hidecode221b/LG4X) by [Hideki Nakajima](https://github.com/hidecode221b).

LG4X-V2 is &copy; 2022-2023 by [Julian Andreas Hochhaus](https://github.com/Julian-Hochhaus). It is based on [LG4X](https://github.com/hidecode221b/LG4X)  &copy; 2020-2023 by [Hideki Nakajima](https://github.com/hidecode221b).

LG4X-V2 is build upon the ['lmfit'-package](https://github.com/lmfit/lmfit-py) using 'PyQt5' for the GUI.

## Installation:

LG4X-V2 is build upon the 'lmfit'-package using 'PyQt5' for the GUI.
LG4X-V2 could be installed by cloning the repository and afterwards installing all package requirements:

```
git clone https://github.com/Julian-Hochhaus/LG4X-V2.git
cd LG4X-V2/
```

LG4X-V2 depends on the following packages and versions:
```
asteval>=0.9.28
lmfit>=1.1.0
matplotlib>=3.6
numpy>=1.19
pandas>=2.0
PyQt5>=5.15
scipy>=1.6
uncertainties>=3.1.4
lmfitxps>=2.4.1
```

These requirements could be installed using ``pip``:
```
pip install -r requirements.txt
```

### Cite the project

If LG4X-V2 has been significant in your research, and you would like to acknowledge the project in your academic publication, we suggest citing the software using zenodo:

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7777422.svg)](https://doi.org/10.5281/zenodo.7777422)

You can use our [CITATION.cff](https://github.com/Julian-Hochhaus/LG4X-V2/blob/master/CITATION.cff) too to generate a citation.


### Publications
Below is a selection of publications that have made use of LG4X-V2. If you have used LG4X-V2 for your publication and would like to be mentioned in the list, please let us know:

- K. Teenakul et al. [Treatment of carbon electrodes with Ti3C2Tx MXene coating and thermal method for vanadium redox flow batteries: a comparative study](https://doi.org/10.1039/D4RA01380H) RSC Adv., **14**, 12807-12816 (2024).

- P. Weinert et al. [Structural, chemical, and magnetic investigation of a graphene/cobalt/platinum multilayer system on silicon carbide](http://dx.doi.org/10.1088/1361-6528/ad1d7b) Nanotechnology, **35** 165702 (2024). 

- P. Lamichhane et al. [Investigating the synergy of rapidly synthesized iron oxide predecessor and plasma-gaseous species for dye-removal to reuse water in irrigation](https://doi.org/10.1016/j.chemosphere.2024.143040) Chemosphere, **24** 143040 (2024).

- P. Weinert [Structural, chemical, and magnetic investigation of a graphene/cobalt/platinum multilayer system on silicon carbide : About the formation of magnetic structures in 2D cobalt layers](https://d-nb.info/1328839591) Dissertation (2024).

- J. A. Hochhaus et al. [Structural analysis of Sn on Au(111) at low coverages: Towards the Au2Sn surface alloy with alternating fcc and hcp domains](https://doi.org/10.1038/s41598-025-91733-2) Sci. Rep. **15**, 7953 (2025). 

- T.R. Acharya et al. [Non-thermal plasma-mediated green synthesis of chitosan-functionalized gold nanoparticles for enhanced cancer immunogenicity](https://doi.org/10.1016/j.jiec.2025.06.029) J. Ind. Eng. Chem. **36** (2025).
  
- J. A. Hochhaus et al. [First evidence of a square-like Sn lattice on the Au2Sn surface alloy on Au(111)](https://doi.org/10.1016/j.apsusc.2025.164470) Appl. Surf. Sci., 164470 (2025). 
  
### License

LG4X-V2 is distributed under [MIT license](https://github.com/Julian-Hochhaus/LG4X-V2/blob/master/LICENSE). 

### Contributing

We would love your help, either as ideas, documentation, or code. If you have a new algorithm or want to add or fix existing code, please do! Here's how you can get started:

1. Fork the LG4X-V2 repository on [GitHub](https://github.com/Julian-Hochhaus/LG4X-V2/fork).
2. Clone your forked repository by running the command: 
`git clone https://github.com/<your name>/LG4X-V2.git`.
3. Install all dependencies by running 
`pip install -r requirements.txt`.
4. Create a new branch for your awesome new feature with `git checkout -b <awesome_new_feature>`.
5. Start coding!
6. Verify that your feature does not break anything.
7. Push your changes to your fork by running `git push origin`.
8. Open a pull request on [the LG4X-V2 repository](https://github.com/Julian-Hochhaus/LG4X-V2/pulls).

If you need any additional help, please visit our [GitHub discussions page](https://github.com/Julian-Hochhaus/LG4X-V2/discussions).
#### Thank you to the contributors of LG4X-V2!



<div align="center">

[<img src="https://avatars.githubusercontent.com/u/22680429?v=4" width="100" height="100">](https://github.com/Julian-Hochhaus) | [<img src="https://avatars.githubusercontent.com/u/3158208?v=4" width="100" height="100">](https://github.com/hidecode221b) | [<img src="https://avatars.githubusercontent.com/u/100384348?v=4" width="100" height="100">](https://github.com/Hexanders) | [<img src="https://avatars.githubusercontent.com/u/32986815?v=4" width="100" height="100">](https://github.com/SHilgers) | [<img src="https://avatars.githubusercontent.com/in/29110?v=4" width="100" height="100">](https://github.com/apps/dependabot) |
|---|---|---|---|---|
[Julian-Hochhaus](https://github.com/Julian-Hochhaus) | [hidecode221b](https://github.com/hidecode221b) | [Hexanders](https://github.com/Hexanders) | [SHilgers](https://github.com/SHilgers) | [dependabot[bot]](https://github.com/apps/dependabot) |

</div>








### Code of Conduct

LG4X-V2 is committed to fostering a welcoming community. Please have a look at our [Code of Conduct](https://github.com/Julian-Hochhaus/LG4X-V2/blob/master/CODE_OF_CONDUCT.md).


## Note: 

**The following README was not yet updated and was written by [Hideki NAKAJIMA](https://github.com/hidecode221b) for [LG4X](https://github.com/hidecode221b/LG4X), therefore the interface of LG4X-V2 is different to the examples shown in the README and several features of LG4X-V2 are not yet documented!**


LG4X provides a graphical user interface for [XPS](https://en.wikipedia.org/wiki/X-ray_photoelectron_spectroscopy) curve fitting analysis based on the [lmfit](https://pypi.org/project/lmfit/) package, which is the non-linear least-square minimization method on python platform. LG4X facilitates the curve fitting analysis for python beginners. LG4X was developed on [Python 3](https://www.python.org/), and [PyQt5](https://pypi.org/project/PyQt5/) was used for its graphical interface design. [Shirley](https://doi.org/10.1103/PhysRevB.5.4709) and [Tougaard](https://doi.org/10.1002/sia.740110902) iterated methods are implemented as a supplementary code for XPS background subtraction. LG4X tidies up all fitting parameters with their bound conditions in table forms. Fitting parameters can be imported and exported as a preset file before and after analysis to streamline the fitting procedures. Fitting results are also exported as a text for parameters and csv file for spectral data. In addition, LG4X simulates the curve without importing data and evaluates the initial parameters over the data plot prior to optimization.
## Methods

#### Supplementary codes for XPS analysis

[xpspy.py](https://github.com/heitler/LG4X/blob/master/Python/xpspy.py) should be located in the same directory as [main.py](https://github.com/heitler/LG4X/blob/master/Python/main.py) for XPS energy range selection for background (BG) subtraction in Shirley and Tougaard methods, which are taken from codes by [Kane O'Donnell](https://github.com/kaneod/physics/blob/master/python/specs.py) and [James Mudd](https://warwick.ac.uk/fac/sci/physics/research/condensedmatt/surface/people/james_mudd/igor/).

[vamas.py](https://github.com/heitler/LG4X/blob/master/Python/vamas.py) and [vamas_export.py](https://github.com/heitler/LG4X/blob/master/Python/vamas_export.py) are also necessary for importing ISO [VAMAS](https://doi.org/10.1002/sia.740130202) format file. vamas.py is a modifed class of VAMAS format from [Kane O'Donnell](https://github.com/kaneod/physics/blob/master/python/vamas.py).

[periodictable.py](https://github.com/heitler/LG4X/blob/master/Python/periodictable.py) and [periodictableui.py](https://github.com/heitler/LG4X/blob/master/Python/periodictableui.py) are the periodic table window to identify the peak elements. The codes are based on and revised from [clusterid](https://github.com/BrendanSweeny/clusterid).

[elements.py](https://github.com/heitler/LG4X/blob/master/Python/elements.py) and [elementdata.py](https://github.com/heitler/LG4X/blob/master/Python/elementdata.py) are the class for peak energy and sensitivity used in the priodic table above. The codes are based on and revised from [clusterid](https://github.com/BrendanSweeny/clusterid).

### Start LG4X

> `python3 main.py`

#### Testing and developing environment

* Python 3.9.5
* asteval==0.9.23
* lmfit==1.0.2
* matplotlib==3.4.3
* numpy==1.20.3
* pandas==1.3.2
* PyQt5==5.15.4
* scipy==1.6.3
* uncertainties==3.1.5

### Usage

1. Import data
    - Import csv, text, or vamas (.vms/.npl) file format.
    - All csv and text files in a directory.
    - Choose data from file list if it was already imported.
1. Setup background and peak parameters with their types
    - Select energy range of spectrum for optimization.
    - Setup initial BG parameters including polynomial coefficients.
    - Setup peak model and its parameters.
    - Increase and decrease the number of peaks.
    - Load a preset file if available.
1. Evaluate parameters
    - Plot the curves without optimization.
    - Simulate the curves based on the range and peaks if no data file is selected in the File list.
1. Fit curve
    - Adjust parameters and bounds until they become converged
1. Export results
    - Export csv file for curves
    - Export text file for parameters
    - Save parameters as a preset for next analysis

## Export csv file for curves
The exported .csv file contains the raw data as well as all fitted components:
Thereby, the first and second column contain the input data, respectively the x and y data.
The third column contains the intensity data minus the background. 
In the forth column, the sum over all components is given, if you wish to plot your data without background, this would be the sum curve over all components you wish to plot.
In column five and six, the background and the polynomial background are given. Important to note that the background already contains the polynomial background, the polynomial background in column six is only given because LG4X-V2 adds a polynomial background to each fit, if the parameters pg_i are not fixed to 0.
In the seventh column, the sum curve over all components and backgrounds is given, that's the sum curve you wish to plot if you are using the raw intensities including the background to present your data.
The following columns contain the components of the fit model.


#### Home directory to import data

You can change the HOME directory in the main.py edited in a way below. `#` makes a line comment out. 

> `# Home directory`
> 
> `self.filePath = QtCore.QDir.homePath()`
> 
> `# self.filePath = '/Users/hidekinakajima/Desktop/WFH2021_2/lg4x/LG4X-master/Python/'`
> 



## Video

[YouTube: Introduction of LG4X](https://youtu.be/cDXXXBfWU1w)

[YouTube: Installation of LG4X in miniconda3 environment](https://youtu.be/cEbo6ZHlK-U)





## Database reference
X-ray data booklet for binding energy
- http://xdb.lbl.gov/

"Hartree-Slater subshell photoionization cross-sections at 1254 and 1487 eV"
J. H. Scofield, Journal of Electron Spectroscopy and Related Phenomena, 8129-137 (1976).
- http://dx.doi.org/10.1016/0368-2048(76)80015-1
- https://a-x-s.org/research/cross-sections/

"Calculated Auger yields and sensitivity factors for KLL-NOO transitions with 1-10 kV primary beams"
S. Mroczkowski and D. Lichtman, J. Vac. Sci. Technol. A 3, 1860 (1985).
- http://dx.doi.org/10.1116/1.572933
- http://www.materialinterface.com/wp-content/uploads/2014/11/Calculated-AES-yields-Matl-Interface.pdf

(Electron beam energy at 1, 3, 5, and 10 keV for relative cross section and derivative factors)


## Interface design

An initial gui concept is taken from [here](http://songhuiming.github.io/pages/2016/05/31/read-in-csv-and-plot-with-matplotlib-in-pyqt4/) and [there](https://stackoverflow.com/questions/47964897/how-to-graph-from-a-csv-file-using-matpotlib-and-pyqt5).

![LG4X interface cencept](https://github.com/heitler/LG4X/blob/master/Images/Screen%20Shot%202020-05-24%20at%2021.24.14.png "GUI")

### Buttons

#### Evaluate
You can evaluate the fitting parameters without fitting optimization on data spectrum. If you do not select the data, it works as simulation mode in the range you specify in BG table (`x_min`, `x_max`, the number of data points `pt`).

#### Fit
You can optimize the fitting parameters by least-square method, and parameters in the table are updated after optimization.

#### Export
LG4X exports fitting results in two different files. One is a text file for fitting conditions `_fit.txt`, the other is a csv format file for data `_fit_csv`, which is saved at the same directory of the former file.

#### Add and rem peak
You can add and remove peak at the end of column from the Fit table.

### Drop-down menus

#### Importing data
LG4X imports csv format or tab separated text files. A data file should contain two columns. First column is energy and second column is spectral intensity. LG4X skips first row, because it is typically used for column names. Example data files are available in [Example](https://github.com/hidecode221b/LG4X/tree/master/Example). Energy and instensiy are calibrated in the Excel XPS macro ([EX3ms](https://github.com/hidecode221b/xps-excel-macro)) prior to the analysis for convenience. The method of energy calibration is discussed in the [link](https://doi.org/10.1016/j.pmatsci.2019.100591). 

VAMAS file format can also be imported in LG4X by decomposing a VAMAS file into the tab separated text files based on the block and sample idenfitifers. Exported tab separated text files are available in the same directory as the VAMAS file. You can just use LG4X to convert the VAMAS file into tab separated text files for the other program you prefer. Note that the binding energy scale is automatically created from VAMAS for XPS and UPS data.

Imported data is displayed in the figure and listed in the file list. You can also open the directory to import all csv and text files in the file list. 

#### File list
Imported file path is added in the list. You can choose the path to import a data file again from the list once you import the data file. Fitting parameters are loaded from `Fitting preset` menu below.

#### Fitting preset
Fitting condition can be created in the BG and Fit tables. From fitting preset drop-down menu, you can create the most simple single-peak preset from `New`. If you have a preset previously saved, you can `load` a preset file, which will be listed in the `Fitting preset`. Typical conditions for XPS `C1s` and `C K edge` are also available from the list as examples. A preset filename is ended with `_pars.dat`, and parameters include in the preset file as a list in the following way.

> `[*BG type index*, [*BG table parameters*], [*Fit table parameters*]]`

`Periodic table` is available to identify the peak position and relative intensity based on XPS Al K&#945; excitation source (1486.6 eV). If you change the excitation energy `hn` and work function `wf`, the core-level and Auger peak energies are revised according to the equation below.

> `BE = hn - wf - KE`

`BE` represents the binding energy, and `KE` kinetic energy. The database reference and example usage of periodic table are shown below. `Refresh` button enables us to display elements in the other dataset, and `Clear` button removes all elements.

#### BG types (`Shirley BG` to be shown as a default)
You can choose the BG type to be subtracted from the raw data as listed below. Shirley and Tougaard BG iteration functions are available from xpypy.py, which should be located with main.py. From lmfit [built-in models](https://lmfit.github.io/lmfit-py/builtin_models.html), 3rd-order polynomial and 3 step functions are implemented. Fermi-Dirac (ThermalDistributionModel) is used for the Fermi edge fitting, and arctan and error functions (StepModel) for NEXAFS K edge BG. Polynomial function is added to the other BG models configured in the BG table, so polynomial parameters have to be taken into account for all BG optimization. You can turn off polynomial parameters by filling all zeros with turning on checkbox. Valence band maximum and secondary electron cutoff can be fitted with the 4th polynomial function for the density of states or edge jump at the onset. 

| No. | String | BG model | Parameters |
| --- | --- | --- | --- |
| 0 | | | `x_min`, `x_max` for fitting range, data points in simulation `pt`, `hn`, `wf` |
| 1 | | Shirley BG | Initial `cv`, max iteration number `it` |
| 2 | | Tougaard BG | `B`, `C`, `C'`, `D` |
| 3 | pg | [Polynomial BG](https://lmfit.github.io/lmfit-py/builtin_models.html#polynomialmodel) | c0, c1, c2, c3 |
| 4 | bg | [Fermi-Dirac BG](https://lmfit.github.io/lmfit-py/builtin_models.html#thermaldistributionmodel) | amplitude, center, kt |
| 5 | bg | [Arctan BG](https://lmfit.github.io/lmfit-py/builtin_models.html#stepmodel) | amplitude, center, sigma |
| 6 | bg | [Error BG](https://lmfit.github.io/lmfit-py/builtin_models.html#stepmodel) | amplitude, center, sigma |
| 7 | bg | VBM/cutoff | center, d1, d2, d3, d4 |

### Tables

#### BG table
You can specify the range for fitting region in the first row of BG table. Checkbox works as a constraint at the value beside. Range and polynomial rows are independent from the drop-down menu selection for background.

#### Fit table
All conditions are based on the lmfit [built-in models](https://lmfit.github.io/lmfit-py/builtin_models.html) listed in the Fit table. Peak models are listed below. For standard XPS analysis, amplitude ratios `amp_ratio` and peak differences `ctr_diff` can be setup from their referenced peak `amp_ref` and `ctr_ref`, respectively from drop-down menu in each column. The number of peaks can be varied with `add peak` and `rem peak` buttons. Checkbox can be used for either fixing values or bound conditions if you check beside value. Empty cells do not effect to the optimization.

| No. | String | Peak model | Parameters |
| --- | --- | --- | --- |
| 1 | g | [GaussianModel](https://lmfit.github.io/lmfit-py/builtin_models.html#gaussianmodel) | amplitude`amp`, center`ctr`, sigma`sig` |
| 2 | l | [LorentzianModel](https://lmfit.github.io/lmfit-py/builtin_models.html#lorentzianmodel) | amplitude, center, sigma |
| 3 | v | [VoigtModel](https://lmfit.github.io/lmfit-py/builtin_models.html#voigtmodel) | amplitude, center, sigma, gamma`gam` |
| 4 | p | [PseudoVoigtModel](https://lmfit.github.io/lmfit-py/builtin_models.html#pseudovoigtmodel) | amplitude, center, sigma, fraction`frac` |
| 5 | e | [ExponentialGaussianModel](https://lmfit.github.io/lmfit-py/builtin_models.html#exponentialgaussianmodel) | amplitude, center, sigma, gamma |
| 6 | s | [SkewedGaussianModel](https://lmfit.github.io/lmfit-py/builtin_models.html#skewedgaussianmodel) | amplitude, center, sigma, gamma |
| 7 | a | [SkewedVoigtModel](https://lmfit.github.io/lmfit-py/builtin_models.html#skewedvoigtmodel) | amplitude, center, sigma, gamma, `skew` |
| 8 | b | [BreitWignerModel](https://lmfit.github.io/lmfit-py/builtin_models.html#breitwignermodel) | amplitude, center, sigma, `q` |
| 9 | n | [LognormalModel](https://lmfit.github.io/lmfit-py/builtin_models.html#lognormalmodel) | amplitude, center, sigma |
| 10 | d | [DoniachModel](https://lmfit.github.io/lmfit-py/builtin_models.html#doniachmodel) | amplitude, center, sigma, gamma |

##### Amplitude ratio and energy difference
XPS doublet peaks are splitted by the spin-orbit coupling based on the atomic theory. Spin-orbit interaction depends on the atomic element and its orbit. The energy separation of doublet corresponds to the spin-orbit constant. Amplitude ratio of doublet is based on the degeneracy (2*j*+1) of each total angular quantum number (*j*). LG4X constrains `amp_ratio` and `ctr_diff` from a reference peak `amp_ref` and `ctr_ref` selected by dropdown menus. For example, Ag3*d* has *j*=5/2 and 3/2, and their amplitude ratio corresponds to 3:2. You can setup second peak amplitude ratio by selecting the first peak at *j*=5/2 and `amp_ratio` = 0.67. This means that amplitude of second peak at *j*=3/2 is constrained by a factor of 0.67 against that of first peak. Peak difference parameter also works in a way that second peak position is away from first peak `ctr_ref` by `ctr_diff` = 6 eV as shown in the figure below. 

Note that amplitude used in the lmfit package is equivalent to the peak area that is propoertional to the amount of element in analytical area and depth by XPS. The atomic ratio is evaluated by the peak area normalized by the sensitivity factor. The ratio of sensitivity factors on doublet peaks is the same as that in multiplicity, so the normalized peak area of one doublet peak is the same as that in other one.

A comprehensive review on XPS technique and analytical procedures is available in link below.

> ["X-ray photoelectron spectroscopy: Towards reliable binding energy referencing" G. Greczynski and L. Hultman, Progress in Materials Science 107, 100591 (2020).](https://doi.org/10.1016/j.pmatsci.2019.100591)

## Examples

![XPS C1s spectrum](https://github.com/heitler/LG4X/blob/master/Images/Capture.PNG "XPS C1s spectrum")

![XPS Ag3d spectrum](https://github.com/heitler/LG4X/blob/master/Images/Screen%20Shot%202020-05-27%20at%2023.14.49.png "XPS Ag3d spectrum")

![NEXAFS C K edge spectrum](https://github.com/heitler/LG4X/blob/master/Images/Screen%20Shot%202020-05-22%20at%201.45.37.png "NEXAFS C K edge spectrum")

![UPS Fermi-edge spectrum](https://github.com/heitler/LG4X/blob/master/Images/Screen%20Shot%202020-05-21%20at%2020.11.36.png "UPS Fermi-edge spectrum")

![Simulated spectrum](https://github.com/heitler/LG4X/blob/master/Images/Screen%20Shot%202020-05-22%20at%201.15.35.png "Simulated spectrum")

![Survey scan](https://github.com/heitler/LG4X/blob/master/Images/Screen%20Shot%202021-10-07%20at%200.03.56.png "Survey scan with periodic table")

You can find the VAMAS format data of various spectra from [Spectroscopy Hub](https://spectroscopyhub.com/measurements).

# LG4X-V2: lmfit GUI for XPS

## Planned features/Improvements

- [ ] add tooltip info to GUI [#18](https://github.com/Julian-Hochhaus/LG4X-V2/issues/18)
- [ ] rework the export files, so that additional informations such as fwhm and areas are exported in readable format as well
- [ ] Pause/Interrupt fit button [#5](https://github.com/Julian-Hochhaus/LG4X-V2/issues/5)
- [ ] rewrite the Readme to explain the features introduced in LG4X-V2
- [ ] Export fit parameters as readable table to be able to use them in e.g. a presentation
- [ ] Introduce 'Clear all' button for clearing all parameters/limits etc.




