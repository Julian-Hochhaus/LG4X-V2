---
layout: page
title: About
permalink: /pages/about/
nav_order: 5
---
# About LG4X-V2
 LG4X-V2 is an open-source GUI for X-ray photoemission spectroscopy (XPS) curve fitting based on the python lmfit package. It streamlines the fitting process for easier validation and consistency. It is inspired by its predecessor software [LG4X](https://github.com/hidecode221b/LG4X) by [Hideki Nakajima](https://github.com/hidecode221b).

LG4X-V2 is &copy; 2022-{{ "now" | date: "%Y" }} by [Julian Andreas Hochhaus](https://github.com/Julian-Hochhaus). It is based on [LG4X](https://github.com/hidecode221b/LG4X)  &copy; 2020-{{ "now" | date: "%Y" }} by [Hideki Nakajima](https://github.com/hidecode221b).

LG4X-V2 is build upon the ['lmfit'-package](https://github.com/lmfit/lmfit-py) using 'PyQt5' for the GUI.

### Cite the project

If LG4X-V2 has been significant in your research, and you would like to acknowledge the project in your academic publication, we suggest citing the software using zenodo:\

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.7777422.svg)](https://doi.org/10.5281/zenodo.7777422)\

You can use our [CITATION.cff](https://github.com/Julian-Hochhaus/LG4X-V2/blob/master/CITATION.cff) too to generate a citation.


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

<ul class="list-style-none">
{% for contributor in site.github.contributors %}
  <li class="d-inline-block mr-1">
     <a href="{{ contributor.html_url }}"><img src="{{ contributor.avatar_url }}" width="32" height="32" alt="{{ contributor.login }}"></a>
  </li>
{% endfor %}
</ul>

### Code of Conduct

LG4X-V2 is committed to fostering a welcoming community. Please have a look at our [Code of Conduct](https://github.com/Julian-Hochhaus/LG4X-V2/blob/master/CODE_OF_CONDUCT.md).
