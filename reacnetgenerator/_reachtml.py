# -*- coding: utf-8 -*-
# Generate a web page to show the analysis report

import re
from collections.abc import Mapping
from multiprocessing import Pool
import htmlmin
import openbabel
import scour.scour
from jinja2 import Template
from ._static import _html, _static_js, _static_css, _static_img


class _HTMLResult(object):
    def __init__(self, ReacNetGenerator):
        self._reactionfile = ReacNetGenerator.reactionfilename
        self._resultfile = ReacNetGenerator.resultfilename
        self._imagefile = ReacNetGenerator.imagefilename
        self._nproc = ReacNetGenerator.nproc
        self._templatedict = {
            "speciesline": 10,
            "speciesshownum": 30,
            "reactionsline": 10,
            "reactionsshownum": 20,
        }

    def _report(self):
        self._readdata()
        self._generateresult()

    def _re(self, smi):
        return smi.replace("O", "[O]").replace("C", "[C]").replace("[HH]", "[H]")

    def _readreaction(self):
        reaction = []
        with open(self._reactionfile) as f:
            for line in f:
                sx = line.split()
                s = sx[1].split("->")
                reaction.append((self._re(s[0]), self._re(s[1]), int(sx[0])))
        return reaction

    def _convertsvg(self, smiles):
        obConversion = openbabel.OBConversion()
        obConversion.SetInAndOutFormats("smi", "svg")
        obConversion.AddOption('x')
        mol = openbabel.OBMol()
        obConversion.ReadString(mol, smiles)
        svgfile = obConversion.WriteString(mol)
        return smiles, svgfile

    def _readspecies(self):
        specs = []
        for reac in self._reaction:
            for spec in reac[:2]:
                if not spec in specs:
                    specs.append(spec)
        with Pool(self._nproc) as pool:
            self._svgfiles = {}
            results = pool.imap(self._convertsvg, specs)
            for spec, svgfile in results:
                self._svgfiles[spec] = svgfile
        return specs

    def _readdata(self):
        self._reaction = self._readreaction()
        self._specs = self._readspecies()

    def _generateresult(self):
        self._generatenetwork()
        self._generatesvg()
        self._templatedict["species"] = self._specs
        self._templatedict["reactions"] = self._reaction
        self._templatedict["css"] = ''.join([
            _static_css["bootstrap.min.css"],
            _static_css["creative.min.css"],
            _static_css["magnific-popup.min.css"],
            _html['bk-css']])
        self._templatedict["bkimage"] = _static_img["fire.jpg"]
        self._templatedict["javascript"] = "".join([
            _static_js["jquery.min.js"],
            _static_js["bootstrap.bundle.min.js"],
            _static_js["jquery.easing.min.js"],
            _static_js["scrollreveal.min.js"],
            _static_js["jquery.magnific-popup.min.js"],
            _static_js["creative.min.js"],
        ])
        template = Template(_html["template"])
        webpage = template.render(**self._templatedict)
        with open(self._resultfile, 'w', encoding="utf-8") as f:
            f.write(htmlmin.minify(webpage))

    def _generatenetwork(self):
        with open(self._imagefile) as f:
            svgdata = f.read().strip()
            svgdata = re.sub(r"\d+(\.\d+)?pt", "100%", svgdata, count=2)
            svgdata = re.sub(
                r"""<(\?xml|\!DOCTYPE|\!\-\-)("[^"]*"|'[^']*'|[^'">])*>""", '', svgdata)
        self._templatedict["network_svg"] = svgdata

    def _generatesvg(self):
        self._templatedict["speciessvg"] = []
        for spec in self._specs:
            svgdata = self._svgfiles[spec]
            svgdata = scour.scour.scourString(svgdata)
            svgdata = re.sub(r"\d+(\.\d+)?px", "100%", svgdata, count=2)
            svgdata = re.sub(
                r"""<rect("[^"]*"|'[^']*'|[^'">])*>""", '', svgdata)
            svgdata = re.sub(
                r"""<\?xml("[^"]*"|'[^']*'|[^'">])*>""", '', svgdata)
            svgdata = re.sub(r"""<title>.*?<\/title>""", '', svgdata)
            self._templatedict["speciessvg"].append(
                {"name": spec, "svg": svgdata})