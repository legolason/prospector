import sys
import numpy as np
try:
    import astropy.io.fits as pyfits
except(ImportError):
    import pyfits
sys.path.append('/home/bjohnson/pfs/apps/clusterfitter')
import observate

lsun, pc = 3.846e33, 3.085677581467192e18 #in cgs
to_cgs = lsun/10**( np.log10(4.0*np.pi)+2*np.log10(pc*10) )


def query_phatcat(objname, phottable = 'data/f2_apcanfinal_6phot_v2.fits',
                      crosstable = None,
                      filtcols = ['275','336','475','814','110','160']):
    
    """Read LCJ's catalog for a certain object and return the magnitudes
    and their uncertainties. Can take either AP numbers or ALTIDs"""
    
    ap = pyfits.getdata(phottable)

    if objname[0:2].upper() == 'AP':
        objname = int(objname[2:])
        ind = (ap['id'] == objname)
    else:
        if crosstable is None:
            crosstable = phottable.replace('canfinal_6phot_v2', 'match_known')
        cross = pyfits.getdata(crosstable)
        ind = (cross['altid'] == objname)
        ind = (ap['id'] == cross[ind]['id'][0])
    
    dat = ap[ind][0]
    mags = np.array([dat['MAG'+f] for f in filtcols]).flatten()
    mags_unc = np.array([dat['SIG'+f] for f in filtcols]).flatten()
    flags = None
    
    return mags, mags_unc, flags
        

def load_obs_mmt(filename = None, objname = None, dist = 1e-5, vel = 0.0,
                  wlo = 3750., whi = 7200., verbose = False,
                  phottable = 'data/f2_apcanfinal_6phot_v2.fits',
                  **kwargs):

    obs ={}

    ####### SPECTRUM #######
    if verbose:
        print('Loading data from {0}'.format(filename))

    fluxconv = np.pi * 4. * (dist * 1e6 * pc)**2 / lsun #erg/s/AA/cm^2 to L_sun/AA
    fluxconv *= 5.0e-20 #approximate counts to erg/s/AA/cm^2
    redshift = vel / 2.998e8
    dat = pyfits.getdata(filename)
    hdr = pyfits.getheader(filename)
    
    crpix = (hdr['CRPIX1'] -1) #convert from FITS to numpy indexing
    obs['wavelength'] = (np.arange(dat.shape[1]) - crpix) * hdr['CDELT1'] + hdr['CRVAL1']
    obs['spectrum'] = dat[0,:] * fluxconv
    obs['unc'] = np.sqrt(dat[1,:]) * fluxconv
    
    #Masking.  should move to a function that reads a mask definition file
    #one should really never mask in the rest frame - that should be modeled!
    obs['mask'] =  ((obs['wavelength'] >= wlo ) & (obs['wavelength'] <= whi))
    obs['mask'] = obs['mask'] & ((obs['wavelength'] <= 5570) | (obs['wavelength'] >= 5590)) #mask OI sky line
    obs['wavelength'] /= (1.0 + redshift)

    ######## PHOTOMETRY ########
    if verbose:
        print('Loading mags from {0} for {1}'.format(phottable, objname))
    mags, mags_unc, flag = query_phatcat(objname, phottable = phottable)
    
    obs['filters'] = observate.load_filters(['wfc3_uvis_'+b.lower() for b in ["F275W", "F336W", "F475W", "F814W"]] +
                                            ['wfc3_ir_'+b.lower() for b in ["F110W", "F160W"]])
    obs['mags'] = mags - (5.0 * np.log10(dist) + 25) - np.array([f.ab_to_vega for f in obs['filters']])
    obs['mags_unc'] = mags_unc

    return obs

def load_obs_lris(filename = None, objname = None, dist = 1e-5, vel = 0.0,
                  wlo = 3550., whi = 5500., verbose = False,
                  phottable = 'data/f2_apcanfinal_6phot_v2.fits',
                  **kwargs):

    obs ={}
    
    ####### SPECTRUM #######
    if verbose:
        print('Loading data from {0}'.format())

    fluxconv = np.pi * 4. * (dist * 1e6 * pc)**2 / lsun #erg/s/AA/cm^2 to L_sun/AA
    redshift = vel / 2.998e8
    dat = pyfits.getdata(filename)
    hdr = pyfits.getheader(filename)
    
    obs['wavelength'] = dat[0]['wave_opt']
    obs['spectrum'] = dat[0]['spec']
    obs['unc'] = 1./np.sqrt(dat[0]['ivar'])
    #masking
    obs['mask'] =  ((obs['wavelength'] >= wlo ) & (obs['wavelength'] <= whi))
    obs['wavelength'] /= (1.0 + redshift)
    

    ######## PHOTOMETRY ######
    if verbose:
        print('Loading mags from {0} for {1}'.format(phottable, objname))
    mags, mags_unc, flag = query_phatcat(objname, phottable = phottable)
     
    obs['filters'] = observate.load_filters(['wfc3_uvis_'+b.lower() for b in ["F336W", "F475W", "F814W"]] +
                                            ['wfc3_ir_'+b.lower() for b in ["F110W", "F160W"]])
    obs['mags'] = mags - (5.0 * np.log10(dist) + 25) - np.array([f.ab_to_vega for f in obs['filters']])
    obs['mags_unc'] = mags_unc

    return obs
