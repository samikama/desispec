"""
Run integration test for QuickLook pipeline

python -m desispec.test.integration_test_quicklook
"""
from shutil import copyfile
import os
import sys
import argparse
import desiutil.log as logging
from desispec.util import runcmd

desi_templates_available = 'DESI_ROOT' in os.environ
desi_root_available = 'DESI_ROOT' in os.environ

#- Default values for all arguments unless told otherwise 
def parse(options=None):
    """
    Can change night or number of spectra to be simulated and delete all output of test
    Won't overwrite exisiting data unless overwrite argument provided

    QuickLook data can be read from $QL_SPEC_DATA if specified
    QuickLook output can be written to $QL_SPEC_REDUX if specified

    Environment Variable check included here
    (different variables necessary depending on arguments provided)
    """
    parser=argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--night',type=str,default='20160728',help='night to be simulated')
    parser.add_argument('--nspec',type=int,default=5,help='number of spectra to be simulated, starting from first')
    parser.add_argument('--overwrite', action='store_true', help='overwrite existing files')
    parser.add_argument('--delete', action='store_true', help='delete all files generated by this test')
    parser.add_argument('--ql_data', action='store_true', help='read data from $QL_SPEC_DATA instead of $DESI_SPECTRO_DATA')
    parser.add_argument('--ql_redux', action='store_true', help='write output to $QL_SPEC_REDUX instead of $DESI_SPECTRO_REDUX/QL/$SPECPROD')

    if options is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(options)

    log = logging.get_logger()
    log.setLevel(logging.DEBUG)
    missing_env = False

    if 'DESI_BASIS_TEMPLATES' not in os.environ:
        log.warning('missing $DESI_BASIS_TEMPLATES needed for simulating spectra'.format(name))
        missing_env = True

    if not os.path.isdir(os.getenv('DESI_BASIS_TEMPLATES')):
        log.warning('missing $DESI_BASIS_TEMPLATES directory')
        log.warning('e.g. see NERSC:/project/projectdirs/desi/spectro/templates/basis_templates/v1.0')
        missing_env = True

    for name in (
        'DESI_SPECTRO_SIM', 'PIXPROD', 'DESIMODEL'):
        if name not in os.environ:
            log.warning("missing ${}".format(name))
            missing_env = True

    if args.ql_redux:
        if 'QL_SPEC_REDUX' not in os.environ:
            log.warning("missing ${}".format('QL_SPEC_REDUX'))
            missing_env = True
    else:
        for name in (
            'DESI_SPECTRO_REDUX', 'SPECPROD'):
            if name not in os.environ:
                log.warning("missing ${}".format(name))
                missing_env = True

    if args.ql_data:
        if 'QL_SPEC_DATA' not in os.environ:
            log.warning("missing ${}".format('QL_SPEC_DATA'))
            missing_env = True
    else:
        if 'DESI_SPECTRO_DATA' not in os.environ:
            log.warning("missing ${}".format('DESI_SPECTRO_DATA'))
            missing_env = True

    if missing_env:
        log.warning("Why are these needed?")
        log.warning("    Simulations written to $DESI_SPECTRO_SIM/$PIXPROD")
        log.warning("    Raw data read from $DESI_SPECTRO_DATA/QL or $QL_SPEC_DATA")
        log.warning("    Spectro/QuickLook pipeline output written to $DESI_SPECTRO_REDUX/QL/$SPECPROD or $QL_SPEC_REDUX")
        log.warning("    PSF files are found in $DESIMODEL")
        log.warning("    Templates are read from $DESI_BASIS_TEMPLATES")

    #- Wait until end to raise exception so that we report everything that
    #- is missing before actually failing
    if missing_env:
        log.critical("missing env vars; exiting without running simulations or quicklook pipeline")
        sys.exit(1)

    sim_dir = os.path.join(os.environ['DESI_SPECTRO_SIM'],os.environ['PIXPROD'],args.night)
    if args.ql_data:
        data_dir = os.path.join(os.environ['QL_SPEC_DATA'],args.night)
    else:
        data_dir = os.path.join(os.environ['DESI_SPECTRO_DATA'],'QL',args.night)
    if args.ql_redux:
        output_dir = os.environ['QL_SPEC_REDUX']
    else:
        output_dir = os.path.join(os.environ['DESI_SPECTRO_REDUX'],'QL',os.environ['SPECPROD'])

    if args.overwrite:
        if os.path.exists(sim_dir):
            sim_files = os.listdir(sim_dir)
            for file in range(len(sim_files)):
                sim_file = os.path.join(sim_dir,sim_files[file])
                os.remove(sim_file)
            os.rmdir(sim_dir)
        if os.path.exists(data_dir):
            data_files = os.listdir(data_dir)
            for file in range(len(data_files)):
                data_file = os.path.join(data_dir,data_files[file])
                os.remove(data_file)
            os.rmdir(data_dir)
        if os.path.exists(output_dir):
            exp_dir = os.path.join(output_dir,'exposures',args.night)
            calib_dir = os.path.join(output_dir,'calib2d',args.night)
            if os.path.exists(exp_dir):
                id_dir = os.path.join(exp_dir,'00000002')
                if os.path.exists(id_dir):
                    id_files = os.listdir(id_dir)
                    for file in range(len(id_files)):
                        id_file = os.path.join(id_dir,id_files[file])
                        os.remove(id_file)
                    os.rmdir(id_dir)
                exp_files = os.listdir(exp_dir)
                for file in range(len(exp_files)):
                    exp_file = os.path.join(exp_dir,exp_files[file])
                    os.remove(exp_file)
                os.rmdir(exp_dir)
            if os.path.exists(calib_dir):
                calib_files = os.listdir(calib_dir)
                for file in range(len(calib_files)):
                    calib_file = os.path.join(calib_dir,calib_files[file])
                    os.remove(calib_file)
                os.rmdir(calib_dir)            

    else:
        if os.path.exists(sim_dir) or os.path.exists(data_dir) or os.path.exists(output_dir):
            raise RuntimeError('Files already exist for this night! Can overwrite or change night if necessary')

    return args

def sim(night, nspec, ql_data, ql_redux):
    """
    Simulate data as part of the QuickLook integration test.

    Args:
        night (str): YEARMMDD
        nspec (int): number of spectra to simulate
        ql_data (str) : data read from $QL_SPEC_DATA if specified
        ql_redux (str) : output sent to $QL_SPEC_REDUX if specified
 
    Raises:
        RuntimeError if any script fails
    """

#    psf_b = os.path.join(os.environ['DESIMODEL'],'data','specpsf','psf-b.fits')
    psf_r = os.path.join(os.environ['DESIMODEL'],'data','specpsf','psf-r.fits')
    psf_z = os.path.join(os.environ['DESIMODEL'],'data','specpsf','psf-z.fits')

    #- Create files needed to run quicklook
    sim_dir = os.path.join(os.environ['DESI_SPECTRO_SIM'],os.environ['PIXPROD'],night)
    if ql_data == 'Use $QL_SPEC_DATA':
        data_dir = os.path.join(os.environ['QL_SPEC_DATA'],night)
    else:
        data_dir = os.path.join(os.environ['DESI_SPECTRO_DATA'],'QL',night)
    if ql_redux == 'Use $QL_SPEC_REDUX':
        output_dir = os.environ['QL_SPEC_REDUX']
    else:
        output_dir = os.path.join(os.environ['DESI_SPECTRO_REDUX'],'QL',os.environ['SPECPROD'])
    exp_dir = os.path.join(output_dir,'exposures',night)
    calib_dir = os.path.join(output_dir,'calib2d',night)

    for expid, flavor in zip([0,1,2], ['arc', 'flat', 'dark']):

        cmd = "newexp-desi --flavor {} --nspec {} --night {} --expid {}".format(flavor,nspec,night,expid)
        if runcmd(cmd) != 0:
            raise RuntimeError('newexp failed for {} exposure {}'.format(flavor, expid))

        if flavor == 'dark':
            cmd = "pixsim-desi --night {} --expid {} --nspec {} --rawfile {}/desi-{:08d}.fits.fz".format(night,expid,nspec,data_dir,expid)
            if runcmd(cmd) != 0:
                raise RuntimeError('pixsim failed for {} exposure {}'.format(flavor, expid))

        if flavor == 'arc' or flavor == 'flat':
            cmd = "pixsim-desi --night {} --expid {} --nspec {} --rawfile {}/desi-{:08d}.fits.fz --preproc --preproc_dir {}".format(night,expid,nspec,data_dir,expid,data_dir)
            if runcmd(cmd) != 0:
                raise RuntimeError('pixsim failed for {} exposure {}'.format(flavor, expid))

        if flavor == 'flat':

#            cmd = "desi_extract_spectra -i {}/pix-b0-00000001.fits -o {}/frame-b0-00000001.fits -f {}/fibermap-00000001.fits -p {} -w 3550,5730,0.8 -n {}".format(data_dir,exp_dir,sim_dir,psf_b,nspec)
#            if runcmd(cmd) != 0:
#                raise RuntimeError('desi_extract_spectra failed for camera b0')

            cmd = "desi_extract_spectra -i {}/pix-r0-00000001.fits -o {}/frame-r0-00000001.fits -f {}/fibermap-00000001.fits -p {} -w 5630,7740,0.8 -n {}".format(data_dir,exp_dir,sim_dir,psf_r,nspec)
            if runcmd(cmd) != 0:
                raise RuntimeError('desi_extract_spectra failed for camera r0')

            cmd = "desi_extract_spectra -i {}/pix-z0-00000001.fits -o {}/frame-z0-00000001.fits -f {}/fibermap-00000001.fits -p {} -w 7650,9830,0.8 -n {}".format(data_dir,exp_dir,sim_dir,psf_z,nspec)
            if runcmd(cmd) != 0:
                raise RuntimeError('desi_extract_spectra failed for camera z0')

        copyfile(os.path.join(sim_dir,'fibermap-{:08d}.fits'.format(expid)),os.path.join(data_dir,'fibermap-{:08d}.fits'.format(expid)))
        os.remove(os.path.join(data_dir,'simpix-{:08d}.fits'.format(expid)))

    for camera in ['r0','z0']:

        cmd = "desi_compute_fiberflat --infile {}/frame-{}-00000001.fits --outfile {}/fiberflat-{}-00000001.fits".format(exp_dir,camera,calib_dir,camera)
        if runcmd(cmd) != 0:
            raise RuntimeError('desi_compute_fiberflat failed for camera {}'.format(camera))

        cmd = "desi_bootcalib --fiberflat {}/pix-{}-00000001.fits --arcfile {}/pix-{}-00000000.fits --outfile {}/psfboot-{}.fits".format(data_dir,camera,data_dir,camera,calib_dir,camera)
        if runcmd(cmd) != 0:
            raise RuntimeError('desi_bootcalib failed for camera {}'.format(camera))

    return

def integration_test(args=None):
    """
    Run an integration test from raw data simulations through QuickLook pipeline

    Args:
        night (str, optional): YEARMMDD
        nspec (int, optional): number of spectra to simulate
        overwrite (bool, otional) : overwrite existing files
        delete (bool, optional) : delete all inputs and outputs
        ql_data (bool, optional) : read data from $QL_SPEC_DATA
        ql_redux (bool, optional) : write files to $QL_SPEC_REDUX

    Raises:
        RuntimeError if QuickLook fails
    """
    #- Parse arguments and check environment variables
    args = parse(args)

    night = args.night
    nspec = args.nspec
    expid = 2
    flat_expid = 1

    if args.ql_data:
        ql_data = 'Use $QL_SPEC_DATA'
        raw_dir = os.environ['QL_SPEC_DATA']
    else:
        ql_data = 'Use $DESI_SPECTRO_DATA'
        raw_dir = os.path.join(os.environ['DESI_SPECTRO_DATA'],'QL')
    if args.ql_redux:
        ql_redux = 'Use $QL_SPEC_REDUX'
        output_dir = os.environ['QL_SPEC_REDUX']
    else:
        ql_redux = 'Use $DESI_SPECTRO_REDUX/QL/$SPECPROD'
        output_dir = os.path.join(os.environ['DESI_SPECTRO_REDUX'],'QL',os.environ['SPECPROD'])
    calib_dir = os.path.join(output_dir,'calib2d',night)

    #- Simulate inputs
    sim(night=night, nspec=nspec, ql_data=ql_data, ql_redux=ql_redux)

    for camera in ['r0','z0']:

        # find necessary input files
        psffile = os.path.join(calib_dir,'psfboot-{}.fits'.format(camera))
        fiberflatfile = os.path.join(calib_dir,'fiberflat-{}-{:08d}.fits'.format(camera,flat_expid))

        #- Verify that quicklook pipeline runs
        com = "desi_quicklook -n {} -c {} -e {} -f {} --psfboot {} --fiberflat {} --rawdata_dir {} --specprod_dir {}".format(night,camera,expid,'dark',psffile,fiberflatfile,raw_dir,output_dir)
        if runcmd(com) != 0:
            raise RuntimeError('quicklook pipeline failed for camera {}'.format(camera))

        #- lastframe files are output to current working directory
        #- should fix this, but will delete this file for now
        os.remove('lastframe-{}-{:08d}.fits'.format(camera,expid))

    #- Remove all output if desired
    if args.delete:
        sim_dir = os.path.join(os.environ['DESI_SPECTRO_SIM'],os.environ['PIXPROD'],args.night)
        if os.path.exists(sim_dir):
            sim_files = os.listdir(sim_dir)
            for file in range(len(sim_files)):
                sim_file = os.path.join(sim_dir,sim_files[file])
                os.remove(sim_file)
            os.rmdir(sim_dir)
        data_dir = os.path.join(raw_dir,night)
        if os.path.exists(data_dir):
            data_files = os.listdir(data_dir)
            for file in range(len(data_files)):
                data_file = os.path.join(data_dir,data_files[file])
                os.remove(data_file)
            os.rmdir(data_dir)
        if os.path.exists(output_dir):
            exp_dir = os.path.join(output_dir,'exposures',night)
            if os.path.exists(exp_dir):
                id_dir = os.path.join(exp_dir,'00000002')
                if os.path.exists(id_dir):
                    id_files = os.listdir(id_dir)
                    for file in range(len(id_files)):
                        id_file = os.path.join(id_dir,id_files[file])
                        os.remove(id_file)
                    os.rmdir(id_dir)
                exp_files = os.listdir(exp_dir)
                for file in range(len(exp_files)):
                    exp_file = os.path.join(exp_dir,exp_files[file])
                    os.remove(exp_file)
                os.rmdir(exp_dir)
            if os.path.exists(calib_dir):
                calib_files = os.listdir(calib_dir)
                for file in range(len(calib_files)):
                    calib_file = os.path.join(calib_dir,calib_files[file])
                    os.remove(calib_file)
                os.rmdir(calib_dir)

if __name__ == '__main__':
    integration_test()
