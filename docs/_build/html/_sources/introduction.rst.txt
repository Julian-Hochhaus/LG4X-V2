.. include:: note.rst

LG4X-V2
========

LG4X-V2 is an open-source GUI for X-ray photoemission spectroscopy (XPS) curve fitting based on the Python ``lmfit`` package. It streamlines the fitting process for easier validation and consistency. It is inspired by its predecessor software LG4X https://github.com/hidecode221b/LG4X by Hideki Nakajima.


Installation
============
.. index:: installation, requirements

Stable Version
--------------
LG4X-V2 is built upon the ``lmfit`` and ``lmfitxps`` package using ``PyQt5`` for the GUI.

Download the latest release if you want to use the (hopefully) stable version:


https://github.com/Julian-Hochhaus/LG4X-V2/releases


Development Version
-------------------

To install the development version or contribute to ``LG4X-V2``, please clone the GitHub repository:


.. code-block:: bash

    git clone https://github.com/Julian-Hochhaus/LG4X-V2.git

Dependencies
------------

After downloading the code, you have to install the following packages in order for the software to work as intended:

.. code-block:: text

    asteval>=0.9.28
    lmfit>=1.1.0
    matplotlib>=3.6
    numpy>=1.19
    pandas>=2.0
    PyQt5>=5.15
    scipy>=1.6
    uncertainties>=3.1.4
    lmfitxps>=4.1.0

This could be done by navigating to the main folder of the software and installing the required packages using ``pip``:

.. code-block:: bash

    pip install -r requirements.txt


Getting Started
===============

While ``lmfit`` provides simple tools to build complex fitting models for non-linear least-squares problems and applies these models to real data, as well as introduces several built-in models, ``lmfitxps`` acts as an extension to ``lmfit`` designed for XPS data analysis. 
``lmfitxps`` provides a comprehensive set of functions and models that facilitate the fitting of XPS spectra.

Although ``lmfit`` already provides several useful models for fitting XPS data, it often proves insufficient in adequately representing experimental XPS data out of the box. In the context of XPS experiments, the observed data is a convolution of both the sample's underlying physical properties and a Gaussian component arising from experimental broadening.

This Gaussian distribution serves as an effective approximation for the convolution of three distinct Gaussian broadening functions, each of which contributes to the complex interplay inherent in the photoemission process:

#. Broadening caused by the excitation source.
#. Broadening resulting from thermal broadening and vibration modes (phonon broadening, depending on the material).
#. Broadening introduced by the analyzer/spectrometer.

For further details, please refer to, for example, the `Practical guide for curve fitting in x-ray photoelectron spectroscopy`_ by G.H. Major et al.

.. _Practical guide for curve fitting in x-ray photoelectron spectroscopy: https://pubs.aip.org/avs/jva/article/38/6/061203/1023652/Practical-guide-for-curve-fitting-in-x-ray

``lmfitxps`` therefore provides convolution functions based on scipy's and numpy's convolution functions to enable users to build custom `lmfit CompositeModels <https://lmfit.github.io/lmfit-py/model.html#lmfit.model.CompositeModel>`_ using convolution of models. In addition, ``lmfitxps`` provides several pre-built models that use convolutions with model functions from lmfit and offer users the following options:

.. table:: Model functions
   :widths: 35 65

   +-------------------------------------------+------------------------------------------------------------+
   | Model                                     | Description                                                |
   +===========================================+============================================================+
   |                                           | Convolution of a Gaussian with a Doniach lineshape used to |
   | ``ConvGaussianDoniachSinglett``           | fit singlet XPS peaks such as *s-orbitals*.                |
   |                                           |                                                            |
   +-------------------------------------------+------------------------------------------------------------+
   |                                           | Convolution of a Gaussian with a pair of Doniach lineshapes|
   | ``ConvGaussianDoniachDublett``            | used to fit doublet XPS peaks such as *p-, d-, f-orbitals*.|
   |                                           |                                                            |
   +-------------------------------------------+------------------------------------------------------------+
   |                                           | Convolution of a Gaussian with a Fermi Dirac Step function |
   | ``FermiEdgeModel``                        | using the thermal distribution lineshape from lmfit.       |
   |                                           |                                                            |
   +-------------------------------------------+------------------------------------------------------------+

In addition to models for fitting signals in XPS data, ``lmfitxps`` introduces several background models that can be included in fit models instead of subtracting precalculated backgrounds. This is known as an active approach as suggested by `A. Herrera-Gomez <https://doi.org/10.1002/sia.5453>`_ and generally leads to better fit results.
The available background models are:

.. table:: Background Models
   :widths: 25 75

   +-------------------------------------------+------------------------------------------------------------+
   | Model                                     | Description                                                |
   +===========================================+============================================================+
   |    ``ShirleyBG``                          | The commonly used step-like Shirley background.            |
   +-------------------------------------------+------------------------------------------------------------+
   |    ``TougaardBG``                         | The Tougaard background based on four-parameter loss       |
   |                                           | function (4-PIESCS) as suggested by                        |
   |                                           | `R.Hesse <https://doi.org/10.1002/sia.3746>`_.             |
   +-------------------------------------------+------------------------------------------------------------+
   |    ``SlopeBG``                           | Calculates a sloping background                             |
   +-------------------------------------------+------------------------------------------------------------+

.. _R.Hesse: https://doi.org/10.1002/sia.3746


In addition to these discussed models, ``lmfitxps`` provides all underlying functions that serve as bases for these models. Furthermore, it includes functions for removing Tougaard and Shirley background components before performing data fitting.





