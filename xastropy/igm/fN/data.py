"""
#;+ 
#; NAME:
#; fN.data
#;    Version 1.0
#;
#; PURPOSE:
#;    Module for fN data constraints
#;   07-Nov-2014 by JXP
#;-
#;------------------------------------------------------------------------------
"""

from __future__ import print_function

import numpy as np
import os
from xastropy.xutils import xdebug as xdb
from xastropy.spec import abs_line, voigt
from astropy.io import fits

#from astropy.io import fits, ascii

class fN_Constraint(object):
    """A Class for fN constraints

    Attributes:
       fN_dtype: string
          Constraint type for the fN
           'fN' -- Standard f(N) evaluation
           'MFP' -- MFP
           'LLS' -- LLS incidence 
           'teff' -- tau effective
           'beta' -- slope constraint
       flavor: string
          Specific type of constraint
       comment: string
       ref: string
          Reference
       cosm: string
          Cosmology used (e.g. WMAP05)
       zeval: float
          Redshift where the constraint is evaluated
       data: dict
          Dictionary containing the constraints
    """

    # Initialize with type
    def __init__(self, fN_dtype, zeval=0., ref='', flavor=''):
        self.fN_dtype = fN_dtype  # Should probably check the choice
        self.zeval = zeval
        self.ref = ref
        self.flavor = flavor

    # Read from binary FITS table
    def from_fits_table(self, row):
        # Common items
        common = ['REF','COSM','TYPE','COMMENT']
        self.ref = row['REF']
        self.cosm = row['COSM']
        self.flavor = row['TYPE']
        self.comment = row['COMMENT']

        # zeval
        if 'ZEVAL' in row.array.names: self.zeval = row['ZEVAL']
        elif 'Z_LLS' in row.array.names: self.zeval = row['Z_LLS']
        elif 'Z_MFP' in row.array.names: self.zeval = row['Z_MFP']
        elif 'Z_TEFF' in row.array.names: self.zeval = row['Z_TEFF']
        else:
            raise ValueError('fN.data: No redshift info!')

        # zip the rest
        self.data = dict(zip(row.array.names,row))
        for item in common: self.data.pop(item) # No need to duplicate

    # Output
    def __repr__(self):
        return ('[%s: %s_%s z=%g, ref=%s]' %
                (self.__class__.__name__,
                 self.fN_dtype, self.flavor,
                 self.zeval, self.ref) )


# ###################### ###############
# ###################### ###############
def fn_data_from_fits(fits_file):
    """ Build up a list of fN constraints from a multi-extension FITS file

    Parameters:
       fits_file: string
          Name of FITS file

    Returns:
       fN_list: list
          List of fN_Constraint objects

    JXP 07 Nov 2014
    """

    # List of constraints
    fN_cs = []

    # Read
    if isinstance(fits_file,list):
        for ifile in fits_file:
            tmp_cs = fn_data_from_fits(ifile)
            for cs in tmp_cs: fN_cs.append(cs)
    else:

        hdus = fits.open(fits_file)
        if len(hdus) == 1:
            raise ValueError('fN.data: Expecting a multi-extension fits file -- %s' % fits_file)
    
    
        # Loop through hdu
        for hdu in hdus[1:]:
            data = hdu.data
            # Get ftype
            if 'FN' in data.dtype.names: ftype = 'fN' # Standard f(N) data
            elif 'TAU_LIM' in data.dtype.names: ftype = 'LLS' # LLS survey
            elif 'MFP' in data.dtype.names: ftype = 'MFP' # MFP measurement
            elif 'TEFF' in data.dtype.names: ftype = 'teff' # tau effective (Lya)
            else: 
                raise ValueError('fN.data: Cannot figure out ftype')
    
            # Loop on the Table
            for row in data:
                fNc = fN_Constraint(ftype)
                fNc.from_fits_table(row)
                fN_cs.append(fNc)

    # Return
    return fN_cs
        

## #################################    
## #################################    
## TESTING
## #################################    
if __name__ == '__main__':

    # Read a dataset
    fn_file = os.environ.get('XIDL_DIR')+'IGM/fN_empirical/fn_constraints_z2.5_vanilla.fits'
    k13r13_file = os.environ.get('XIDL_DIR')+'IGM/fN_empirical/fn_constraints_K13R13_vanilla.fits'
    all_fN_cs = fn_data_from_fits([fn_file,k13r13_file])
    print(all_fN_cs)
    #for fN_c in all_fN_cs: print(fN_c)

    # Reproduce the main figure from P14 (data only)
    import matplotlib as mpl
    mpl.rcParams['font.family'] = 'STIXGeneral-Regular'
    #mpl.rcParams['font.family'] = 'stixgeneral'
    from matplotlib import pyplot as plt

    # Remove K12
    fN_cs = [fN_c for fN_c in all_fN_cs if fN_c.ref != 'K02']
    fN_dtype = [fc.fN_dtype for fc in fN_cs]

    fig = plt.figure(figsize=(8, 5))
    fig.clf()
    main = fig.add_axes( [0.1, 0.1, 0.8, 0.8] ) # xypos, xy-size

    # f(N) data
    main.set_ylabel(r'$\log f(N_{\rm HI})$')
    main.set_xlabel(r'$\log N_{\rm HI}$')

    for fN_c in fN_cs: 
        if fN_c.fN_dtype == 'fN':
            # Length
            ip = range(fN_c.data['NPT'])
            val = np.where(fN_c.data['FN'][ip] > -90)[0]
            if len(val) > 0:
                #xdb.set_trace()
                ipv = np.array(ip)[val]
                xval = np.median(fN_c.data['BINS'][:,ipv],0)
                xerror = [ fN_c.data['BINS'][1,ipv]-xval, xval-fN_c.data['BINS'][0,ipv] ]
                yerror = [ fN_c.data['SIG_FN'][1,ipv], fN_c.data['SIG_FN'][0,ipv] ] # Inverted!
                main.errorbar(xval, fN_c.data['FN'][ipv], xerr=xerror, yerr=yerror, fmt='o',
                             label=fN_c.ref)
    main.legend(loc='lower left', numpoints=1)

    # Extras
    inset = fig.add_axes( [0.55, 0.6, 0.25, 0.25] ) # xypos, xy-size
    inset.set_ylabel('Value') # LHS
    inset.xaxis.set_major_locator(plt.FixedLocator(range(5)))
    #lbl1 = r'$\tau_{\rm eff}^{\rm Ly\alpha}'
    inset.xaxis.set_major_formatter(plt.FixedFormatter(['',r'$\tau_{\rm eff}^{\rm Ly\alpha}$',
                                                        r'$\ell(X)_{\rm LLS}$',
                                                        r'$\lambda_{\rm mfp}^{912}$', '']))

    # tau_eff
    try:
        itau = fN_dtype.index('teff') # Passes back the first one
    except:
        raise ValueError('fN.data: Missing teff type')
    inset.errorbar(1, fN_cs[itau].data['TEFF'], yerr=fN_cs[itau].data['SIG_TEFF'], fmt='_')

    # LLS constraint
    try:
        iLLS = fN_dtype.index('LLS') # Passes back the first one
    except:
        raise ValueError('fN.data: Missing LLS type')
    inset.errorbar(2, fN_cs[iLLS].data['LX'], yerr=fN_cs[iLLS].data['SIG_LX'], fmt='_')

    # MFP constraint
    inset2 = inset.twinx()
    try:
        iMFP = fN_dtype.index('MFP') # Passes back the first one
    except:
        raise ValueError('fN.data: Missing MFP type')
    inset2.errorbar(3, fN_cs[iMFP].data['MFP'], yerr=fN_cs[iMFP].data['SIG_MFP'], fmt='_')
    inset2.set_xlim(0,4)
    inset2.set_ylim(0,350)
    inset2.set_ylabel('(Mpc)')

    # Show
    plt.show()

    print('fN.data: All done testing..')