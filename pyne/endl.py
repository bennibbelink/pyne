#!/usr/bin/env python

"""Module for parsing and manipulating data from ENDL evaluations.

For the moment, classes and functions in this module only implement the
specifications relevant to the EEDL (Evaluated Electron Data Library) and the
EPDL (Evaluated Photon Data Library). The formats are described by the
following documents:

"ENDL type formats for the Livermore Evaluated Photon Data Library, EPDL"
https://www.oecd-nea.org/dbdata/data/manual-endf/nds_eval_epdl.pdf

"ENDL type formats for the Livermore Evaluated Electron Data Library, EEDL"
https://www.oecd-nea.org/dbdata/data/manual-endf/nds_eval_eedl.pdf

For more information, contact Davide Mancusi <davide.mancusi@cea.fr>.
"""
from __future__ import print_function, division, unicode_literals

from warnings import warn
from pyne.utils import QAWarning

import pyne.rxdata as rx
import pyne.utils as utils
from pyne import nucname

import numpy as np
import re

warn(__name__ + ' is not yet QA compliant.', QAWarning)

END_OF_TABLE_RE = re.compile(' {71}1')


class Library(rx.RxLib):
    """A class for a file which contains multiple ENDL tables."""
    def __init__(self, fh):
        self.mts = {}
        self.structure = {}
        self.mat_dict = {}
        self.intdict = {
                0: self._linlin,
                2: self._linlin,
                3: self._loglin,
                4: self._linlog,
                5: self._loglog,
                }
        self.fh = fh
        # read headers for all tables
        self._read_headers()

#    def load(self):
#        """load()
#        Read the ENDL file into a NumPy array.
#
#        Returns
#        -------
#        data : np.array, 1d, float64
#            Returns a 1d float64 NumPy array.
#        """
#        opened_here = False
#        if isinstance(self.fh, basestring):
#            fh = open(self.fh, 'r')
#            opened_here = True
#        else:
#            fh = self.fh
#        fh.readline()
#        data = fromendf_tok(fh.read())
#        fh.seek(0)
#        if opened_here:
#            fh.close()
#        return data

    def _read_headers(self):
        opened_here = False
        if isinstance(self.fh, basestring):
            fh = open(self.fh, 'r')
            opened_here = True
        else:
            fh = self.fh

        while True:
            # get header lines
            line1 = fh.readline()
            line2 = fh.readline()

            # EOF?
            if not line2:
                break

            # store the start of the table
            start = fh.tell()

            # parse the first header line
            nuc_zzzaaa = line1[0:6].strip()
            yi = int(line1[7:9].strip() or -1)
            yo = int(line1[10:12].strip() or -1)
            aw_str = line1[13:24]
            aw = utils.endftod(aw_str) if aw_str else np.float64(-1.)
            date = line1[25:31].strip()
            iflag = int(line1[31].strip() or 0)

            # parse the second header line
            rdesc = int(line2[0:2].strip() or -1)
            rprop = int(line2[2:5].strip() or -1)
            rmod = int(line2[5:8].strip() or -1)
            x1_str = line2[21:32]
            x1 = utils.endftod(x1_str or -1.)

            # convert to Pyne native formats
            nuc = nucname.zzzaaa_to_id(nuc_zzzaaa)

            # insert the nucleus in the self.structure dictionary
#            if nuc not in self.structure:
#                self.structure.update(
#                        { nuc: {
#                            'particle_in': [],
#                            'particle_out': [],
#                            'data': {},
#                            'start': start,
#                            }})

            # skip to the end of the table
            line = fh.readline()
            while line and not END_OF_TABLE_RE.match(line):
                line = fh.readline()



    def _linlin(self, e_int, xs, low, high):
        if low is not None or high is not None:
            interp = interp1d(e_int, xs)
            if low in e_int:
                xs = xs[e_int >= low]
                e_int = e_int[e_int >= low]
            elif low is not None and low > e_int[0]:
                low_xs = interp(low)
                xs = np.insert(xs[e_int > low], 0, low_xs)
                e_int = np.insert(e_int[e_int > low], 0, low)
            if high in e_int:
                xs = xs[e_int <= high]
                e_int = e_int[e_int <= high]
            elif high is not None:
                high_xs = interp(high)
                xs = np.append(xs[e_int < high], high_xs)
                e_int = np.append(e_int[e_int < high], high)
        de_int = float(e_int[-1]-e_int[0])
        return np.nansum((e_int[1:]-e_int[:-1]) * (xs[1:]+xs[:-1])/2./de_int)

    def _linlog(self, e_int, xs, low, high):
        if low is not None or high is not None:
            interp = interp1d(np.log(e_int), xs)
            if low in e_int:
                xs = xs[e_int >= low]
                e_int = e_int[e_int >= low]
            elif low is not None and low > e_int[0]:
                low_xs = interp(np.log(low))
                xs = np.insert(xs[e_int > low], 0, low_xs)
                e_int = np.insert(e_int[e_int > low], 0, low)
            if high in e_int:
                xs = xs[e_int <= high]
                e_int = e_int[e_int <= high]
            elif high is not None:
                high_xs = interp(np.log(high))
                xs = np.append(xs[e_int < high], high_xs)
                e_int = np.append(e_int[e_int < high], high)

        de_int = float(e_int[-1]-e_int[0])
        x1 = e_int[:-1]
        x2 = e_int[1:]
        y1 = xs[:-1]
        y2 = xs[1:]
        A = (y1-y2)/(np.log(x1/x2))
        B = y1-A*np.log(x1)
        return np.nansum(A*(x2*np.log(x2) -
                            x1*np.log(x1)-x2+x1) + B*(x2-x1))/de_int

    def _loglin(self, e_int, xs, low, high):
        if low is not None or high is not None:
            interp = interp1d(e_int, np.log(xs))
            if low in e_int:
                xs = xs[e_int >= low]
                e_int = e_int[e_int >= low]
            elif low is not None and low > e_int[0]:
                low_xs = np.e ** interp(low)
                xs = np.insert(xs[e_int > low], 0, low_xs)
                e_int = np.insert(e_int[e_int > low], 0, low)
            if high in e_int:
                xs = xs[e_int <= high]
                e_int = e_int[e_int <= high]
            elif high is not None:
                high_xs = np.e ** interp(high)
                xs = np.append(xs[e_int < high], high_xs)
                e_int = np.append(e_int[e_int < high], high)

        de_int = float(e_int[-1]-e_int[0])
        x1 = e_int[:-1]
        x2 = e_int[1:]
        y1 = xs[:-1]
        y2 = xs[1:]
        A = (np.log(y1)-np.log(y2))/(x1-x2)
        B = np.log(y1) - A*x1
        return np.nansum((y2-y1)/A)/de_int

    def _loglog(self, e_int, xs, low, high):
        if low is not None or high is not None:
            interp = interp1d(np.log(e_int), np.log(xs))
            if low in e_int:
                xs = xs[e_int >= low]
                e_int = e_int[e_int >= low]
            elif low is not None and low > e_int[0]:
                low_xs = np.e ** interp(np.log(low))
                xs = np.insert(xs[e_int > low], 0, low_xs)
                e_int = np.insert(e_int[e_int > low], 0, low)
            if high in e_int:
                xs = xs[e_int <= high]
                e_int = e_int[e_int <= high]
            elif high is not None:
                high_xs = np.e ** interp(np.log(high))
                xs = np.append(xs[e_int < high], high_xs)
                e_int = np.append(e_int[e_int < high], high)

        de_int = float(e_int[-1]-e_int[0])
        x1 = e_int[:-1]
        x2 = e_int[1:]
        y1 = xs[:-1]
        y2 = xs[1:]
        A = - np.log(y2/y1)/np.log(x1/x2)
        B = - (np.log(y1)*np.log(x2) - np.log(y2)*np.log(x1))/np.log(x1/x2)
        return np.nansum(np.e**B / (A+1) * (x2**(A+1) - x1**(A+1))/de_int)



class NotFound(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
