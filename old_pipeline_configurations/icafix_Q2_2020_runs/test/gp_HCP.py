#!/usr/bin/env python2.7
# encoding: utf-8
"""
This file holds code for running HCP preprocessing and image mapping. It
consists of functions:

* hcpPreFS        ... runs HCP PreFS preprocessing
* hcpFS           ... runs HCP FS preprocessing
* hcpPostFS       ... runs HCP PostFS preprocessing
* hcpDiffusion    ... runs HCP Diffusion weighted image preprocessing
* hcpfMRIVolume   ... runs HCP BOLD Volume preprocessing
* hcpfMRISurface  ... runs HCP BOLD Surface preprocessing
* hcpICAFix       ... runs HCP BOLD ICAFix
* hcpPostFix      ... runs HCP BOLD PostFix
* hcpReApplyFix   ... runs HCP BOLD ReApplyFix
* hcpDTIFit       ... runs DTI Fit
* hcpBedpostx     ... runs Bedpost X
* mapHCPData      ... maps results of HCP preprocessing into `images`
                      folder

All the functions are part of the processing suite. They should be called
from the command line using `qunex` command. Help is available through:

`qunex ?<command>` for command specific help
`qunex -o` for a list of relevant arguments and options

There are additional support functions that are not to be used
directly.

Created by Grega Repovs on 2016-12-17.
Code split from dofcMRIp_core gCodeP/preprocess codebase.
Copyright (c) Grega Repovs. All rights reserved.
"""

from gp_core import *
from g_img import *
from g_core import checkFiles
import niutilities.g_exceptions as ge
import os
import re
import os.path
import shutil
import glob
import sys
import traceback
from datetime import datetime
import time

from concurrent.futures import ProcessPoolExecutor
from functools import partial


# ---- some definitions


unwarp = {None: "Unknown", 'i': 'x', 'j': 'y', 'k': 'z', 'i-': 'x-', 'j-': 'y-', 'k-': 'z-'}
PEDir  = {None: "Unknown", "LR": 1, "RL": 1, "AP": 2, "PA": 2}
PEDirMap  = {'AP': 'j-', 'j-': 'AP', 'PA': 'j', 'j': 'PA'}
SEDirMap  = {'AP': 'y', 'PA': 'y', 'LR': 'x', 'RL': 'x'}


# -------------------------------------------------------------------
#
#                       HCP Pipeline Scripts
#

def getHCPPaths(sinfo, options):
    """
    getHCPPaths - documentation not yet available.
    """
    d = {}

    # ---- HCP Pipeline folders

    base                    = options['hcp_Pipeline']

    d['hcp_base']           = base

    d['hcp_Templates']      = os.path.join(base, 'global', 'templates')
    d['hcp_Bin']            = os.path.join(base, 'global', 'binaries')
    d['hcp_Config']         = os.path.join(base, 'global', 'config')

    d['hcp_PreFS']          = os.path.join(base, 'PreFreeSurfer', 'scripts')
    d['hcp_FS']             = os.path.join(base, 'FreeSurfer', 'scripts')
    d['hcp_PostFS']         = os.path.join(base, 'PostFreeSurfer', 'scripts')
    d['hcp_fMRISurf']       = os.path.join(base, 'fMRISurface', 'scripts')
    d['hcp_fMRIVol']        = os.path.join(base, 'fMRIVolume', 'scripts')
    d['hcp_tfMRI']          = os.path.join(base, 'tfMRI', 'scripts')
    d['hcp_dMRI']           = os.path.join(base, 'DiffusionPreprocessing', 'scripts')
    d['hcp_Global']         = os.path.join(base, 'global', 'scripts')
    d['hcp_tfMRIANalysis']  = os.path.join(base, 'TaskfMRIAnalysis', 'scripts')

    d['hcp_caret7dir']      = os.path.join(base, 'global', 'binaries', 'caret7', 'bin_rh_linux64')

    # ---- Key folder in the hcp folder structure

    hcpbase                 = os.path.join(sinfo['hcp'], sinfo['id'] + options['hcp_suffix'])

    d['base']               = hcpbase
    if options['hcp_folderstructure'] == 'initial':
        d['source'] = d['base']
    else:
        d['source'] = os.path.join(d['base'], 'unprocessed')

    d['hcp_nonlin']         = os.path.join(hcpbase, 'MNINonLinear')
    d['T1w_source']         = os.path.join(d['source'], 'T1w')
    d['DWI_source']         = os.path.join(d['source'], 'Diffusion')

    d['T1w_folder']         = os.path.join(hcpbase, 'T1w')
    d['DWI_folder']         = os.path.join(hcpbase, 'Diffusion')
    d['FS_folder']          = os.path.join(hcpbase, 'T1w', sinfo['id'] + options['hcp_suffix'])
    
    # T1w file
    try:
        T1w = [v for (k, v) in sinfo.iteritems() if k.isdigit() and v['name'] == 'T1w'][0]      
        filename = T1w.get('filename', None)
        if filename and options['hcp_filename'] == "original":
            d['T1w'] = "@".join(glob.glob(os.path.join(d['source'], 'T1w', sinfo['id'] + '*' + filename + '*.nii.gz')))
        else:
            d['T1w'] = "@".join(glob.glob(os.path.join(d['source'], 'T1w', sinfo['id'] + '*T1w_MPR*.nii.gz')))
    except:
        d['T1w'] = 'NONE'

    # --- longitudinal FS related paths

    if options['hcp_fs_longitudinal']:
        d['FS_long_template'] = os.path.join(hcpbase, 'T1w', options['hcp_fs_longitudinal'])
        d['FS_long_results']  = os.path.join(hcpbase, 'T1w', "%s.long.%s" % (sinfo['id'] + options['hcp_suffix'], options['hcp_fs_longitudinal']))
        d['FS_long_subject_template'] = os.path.join(options['subjectsfolder'], 'FSTemplates', sinfo['subject'], options['hcp_fs_longitudinal'])
        d['hcp_long_nonlin']          = os.path.join(hcpbase, 'MNINonLinear_' + options['hcp_fs_longitudinal'])
    else:
        d['FS_long_template']         = ""
        d['FS_long_results']          = ""
        d['FS_long_subject_template'] = ""
        d['hcp_long_nonlin']          = ""


    # --- T2w related paths

    if options['hcp_t2'] == 'NONE':
        d['T2w'] = 'NONE'
    else:
        try:
            T2w = [v for (k, v) in sinfo.iteritems() if k.isdigit() and v['name'] == 'T2w'][0]
            filename = T2w.get('filename', None)
            if filename and options['hcp_filename'] == "original":
                d['T2w'] = "@".join(glob.glob(os.path.join(d['source'], 'T2w', sinfo['id'] + '*' + filename + '*.nii.gz')))
            else:
                d['T2w'] = "@".join(glob.glob(os.path.join(d['source'], 'T2w', sinfo['id'] + '_T2w_SPC*.nii.gz')))
        except:
            d['T2w'] = 'NONE'

    # --- Fieldmap related paths

    d['fmapmag']   = ''
    d['fmapphase'] = ''
    d['fmapge']    = ''
    if options['hcp_avgrdcmethod'] == 'SiemensFieldMap' or options['hcp_bold_dcmethod'] == 'SiemensFieldMap':
        d['fmapmag']   = glob.glob(os.path.join(d['source'], 'FieldMap' + options['fmtail'], sinfo['id'] + options['fmtail'] + '*_FieldMap_Magnitude.nii.gz'))
        d['fmapphase'] = glob.glob(os.path.join(d['source'], 'FieldMap' + options['fmtail'], sinfo['id'] + options['fmtail'] + '*_FieldMap_Phase.nii.gz'))
        d['fmapge']    = ""
    elif options['hcp_avgrdcmethod'] == 'GeneralElectricFieldMap' or options['hcp_bold_dcmethod'] == 'GeneralElectricFieldMap':
        d['fmapmag']   = ""
        d['fmapphase'] = ""
        d['fmapge']    = glob.glob(os.path.join(d['source'], 'FieldMap' + options['fmtail'], sinfo['id'] + options['fmtail'] + '*_FieldMap_GE.nii.gz'))

    # --- default check files

    for pipe, default in [('hcp_prefs_check',     'check_PreFreeSurfer.txt'),
                          ('hcp_fs_check',        'check_FreeSurfer.txt'),
                          ('hcp_fslong_check',    'check_FreeSurferLongitudinal.txt'),
                          ('hcp_postfs_check',    'check_PostFreeSurfer.txt'),
                          ('hcp_bold_vol_check',  'check_fMRIVolume.txt'),
                          ('hcp_bold_surf_check', 'check_fMRISurface.txt'),
                          ('hcp_dwi_check',       'check_Diffusion.txt')]:
        if options[pipe] == 'all':
            d[pipe] = os.path.join(options['subjectsfolder'], 'specs', default)
        elif options[pipe] == 'last':
            d[pipe] = False
        else:
            d[pipe] = options[pipe]

    return d


def doHCPOptionsCheck(options, sinfo, command):
    if options['hcp_folderstructure'] not in ['initial', 'hcpls']:
        raise ge.CommandFailed(command, "Unknown HCP folder structure version", "The specified HCP folder structure version is unknown: %s" % (options['hcp_folderstructure']), "Please check the 'hcp_folderstructure' parameter!")

    if options['hcp_folderstructure'] == 'initial':
        options['fctail'] = '_fncb'
        options['fmtail'] = '_strc'
    else:
        options['fctail'] = ""
        options['fmtail'] = ""


def action(action, run):
    """
    action - documentation not yet available.
    """
    if run == "test":
        if action.istitle():
            return "Test " + action.lower()
        else:
            return "test " + action
    else:
        return action



def checkGDCoeffFile(gdcstring, hcp, sinfo, r="", run=True):
    '''
    Function that extract the information on the correct gdc file to be used and tests for its presence;
    '''

    if gdcstring not in ['', 'NONE']:

        if any([e in gdcstring for e in ['|', 'default']]):
            try:
                try:
                    device = {}
                    dmanufacturer, dmodel, dserial = [e.strip() for e in sinfo.get('device', 'NA|NA|NA').split('|')]
                    device['manufacturer'] = dmanufacturer
                    device['model'] = dmodel
                    device['serial'] = dserial
                except:
                    r += "\n---> WARNING: device information for this session is malformed: %s" % (sinfo.get('device', '---'))
                    raise

                gdcoptions = [[ee.strip() for ee in e.strip().split(':')] for e in gdcstring.split('|')]
                gdcfile = [e[1] for e in gdcoptions if e[0] == 'default'][0]
                gdcfileused = 'default'

                for ginfo, gwhat, gfile in [e for e in gdcoptions if e[0] != 'default']:
                    if ginfo in device:
                        if device[ginfo] == gwhat:
                            gdcfile = gfile
                            gdcfileused = '%s: %s' % (ginfo, gwhat)
                            break
                    if ginfo in sinfo:
                        if sinfo[ginfo] == gwhat:
                            gdcfile = gfile
                            gdcfileused = '%s: %s' % (ginfo, gwhat)
                            break
            except:
                r += "\n---> ERROR: malformed specification of gdcoeffs: %s!" % (gdcstring)
                run = False
                raise
            
            if gdcfile in ['', 'NONE']:
                r += "\n---> WARNING: Specific gradient distorsion coefficients file could not be identified! None will be used."
                gdcfile = "NONE"
            else:
                r += "\n---> Specific gradient distorsion coefficients file identified (%s):\n     %s" % (gdcfileused, gdcfile)

        else: 
            gdcfile = gdcstring

        if gdcfile not in ['', 'NONE']:
            if not os.path.exists(gdcfile):
                gdcoeffs = os.path.join(hcp['hcp_Config'], gdcfile)
                if not os.path.exists(gdcoeffs):
                    r += "\n---> ERROR: Could not find gradient distorsion coefficients file: %s." % (gdcfile)
                    run = False
                else:
                    r += "\n---> Gradient distorsion coefficients file present."
            else:
                r += "\n---> Gradient distorsion coefficients file present."
    else:
        gdcfile = "NONE"

    return gdcfile, r, run




def hcpPreFS(sinfo, options, overwrite=False, thread=0):
    '''
    hcp_PreFS [... processing options]
    hcp1 [... processing options]

    USE
    ===

    Runs the pre-FS step of the HCP Pipeline. It looks for T1w and T2w images in
    sessions's T1w and T2w folder, averages them (if multiple present) and
    linearly and nonlinearly aligns them to the MNI atlas. It uses the adjusted
    version of the HCP that enables the preprocessing to run with of without T2w
    image(s). A short name 'hcp1' can be used for this command.

    REQUIREMENTS
    ============

    The code expects the input images to be named and present in the specific
    folder structure. Specifically it will look within the folder:

    <session id>/hcp/<session id>

    for folders and files:

    T1w/*T1w_MPR[N]*
    T2w/*T2w_MPR[N]*

    There has to be at least one T1w image present. If there are more than one
    T1w or T2w images, they will all be used and averaged together.

    Depending on the type of distortion correction method specified by the
    --hcp_avgrdcmethod argument (see below), it will also expect the presence
    of the following files:

    __TOPUP__

    SpinEchoFieldMap[N]*/*_<hcp_sephasepos>_*
    SpinEchoFieldMap[N]*/*_<hcp_sephaseneg>_*

    If there are more than one pair of spin echo files, the first pair found
    will be used.

    __SiemensFieldMap__

    FieldMap/<session id>_FieldMap_Magnitude.nii.gz
    FieldMap/<session id>_FieldMap_Phase.nii.gz

    __GeneralElectricFieldMap__

    FieldMap/<session id>_FieldMap_GE.nii.gz

    RESULTS
    =======

    The results of this step will be present in the above mentioned T1w and T2w
    folders as well as MNINonLinear folder generated and populated in the same
    sessions's root hcp folder.

    RELEVANT PARAMETERS
    ===================

    general parameters
    ------------------

    When running the command, the following *general* processing parameters are
    taken into account:

    --sessions              ... The batch.txt file with all the sessions information
                                [batch.txt].
    --subjectsfolder        ... The path to the study/subjects folder, where the
                                imaging  data is supposed to go [.].
    --cores                 ... How many cores to utilize [1].
    --overwrite             ... Whether to overwrite existing data (yes) or not (no)
                                [no].
    --logfolder             ... The path to the folder where runlogs and comlogs
                                are to be stored, if other than default []
    --log                   ... Whether to keep ('keep') or remove ('remove') the
                                temporary logs once jobs are completed ['keep'].
                                When a comma separated list is given, the log will
                                be created at the first provided location and then 
                                linked or copied to other locations. The valid 
                                locations are: 
                                * 'study'   for the default: 
                                            `<study>/processing/logs/comlogs`
                                            location,
                                * 'session' for `<sessionid>/logs/comlogs
                                * 'hcp'     for `<hcp_folder>/logs/comlogs
                                * '<path>'  for an arbitrary directory
    --hcp_processing_mode   ... Controls whether the HCP acquisition and processing 
                                guidelines should be treated as requirements 
                                (HCPStyleData) or if additional processing 
                                functionality is allowed (LegacyStyleData). In this
                                case running processing w/o a T2w image.
    --hcp_folderstructure   ... Specifies the version of the folder structure to
                                use, 'initial' and 'hcpls' are supported ['hcpls']
    --hcp_filename          ... Specifies whether the standard ('standard') filenames
                                or the specified original names ('original') are to
                                be used ['standard']

    specific parameters
    -------------------

    In addition the following *specific* parameters will be used to guide the
    processing in this step:
    
    --hcp_suffix            ... Specifies a suffix to the session id if multiple
                                variants are run, empty otherwise [].
    --hcp_t2                ... NONE if no T2w image is available and the
                                preprocessing should be run without them,
                                anything else otherwise [t2]. NONE is only valid
                                if 'LegacyStyleData' processing mode was specified.
    --hcp_brainsize         ... Specifies the size of the brain in mm. 170 is FSL
                                default and seems to be a good choice, HCP uses
                                150, which can lead to problems with larger heads
                                [150].
    --hcp_t1samplespacing   ... T1 image sample spacing, NONE if not used [NONE].
    --hcp_t2samplespacing   ... T2 image sample spacing, NONE if not used [NONE].
    --hcp_gdcoeffs          ... Path to a file containing gradient distortion
                                coefficients, alternatively a string describing
                                multiple options (see below), or "NONE", if not 
                                used [NONE].
    --hcp_bfsigma           ... Bias Field Smoothing Sigma (optional) [].
    --hcp_avgrdcmethod      ... Averaging and readout distortion correction
                                method. Can take the following values:
                                NONE
                                ... average any repeats with no readout correction
                                FIELDMAP
                                ... average any repeats and use Siemens field
                                    map for readout correction
                                SiemensFieldMap
                                ... average any repeats and use Siemens field
                                    map for readout correction.
                                GeneralElectricFieldMap
                                ... average any repeats and use GE field map for
                                    readout correction
                                TOPUP
                                ... average any repeats and use spin echo field
                                    map for readout correction.
                                [NONE]
    --hcp_unwarpdir         ... Readout direction of the T1w and T2w images (x,
                                y, z or NONE); used with either a regular field
                                map or a spin echo field map [NONE].
    --hcp_echodiff          ... Difference in TE times if a fieldmap image is
                                used, set to NONE if not used [NONE].
    --hcp_seechospacing     ... Echo Spacing or Dwelltime of Spin Echo Field Map
                                or "NONE" if not used [NONE].
    --hcp_sephasepos        ... Label for the positive image of the Spin Echo 
                                Field Map pair [""]
    --hcp_sephaseneg        ... Label for the negative image of the Spin Echo 
                                Field Map pair [""]
    --hcp_seunwarpdir       ... Phase encoding direction of the Spin Echo Field
                                Map (x, y or NONE) [NONE].
    --hcp_topupconfig       ... Path to a configuration file for TOPUP method
                                or "NONE" if not used [NONE].
    --hcp_prefs_check       ... Whether to check the results of PreFreeSurfer 
                                pipeline by presence of last file generated 
                                ('last'), the default list of all files ('all') 
                                or using a specific check file ('<path to file>')
                                ['last']
    --hcp_prefs_custombrain ... Whether to only run the final registration using
                                either a custom prepared brain mask (MASK) or 
                                custom prepared brain images (CUSTOM), or to 
                                run the full set of processing steps (NONE). [NONE]
                                If a mask is to be used (MASK) then a "
                                custom_acpc_dc_restore_mask.nii.gz" image needs
                                to be placed in the <session>/T1w folder.
                                If a custom brain is to be used (BRAIN), then the
                                following images in <session>/T1w folder need to 
                                be adjusted:
                                - T1w_acpc_dc_restore_brain.nii.gz
                                - T1w_acpc_dc_restore.nii.gz
                                - T2w_acpc_dc_restore_brain.nii.gz
                                - T2w_acpc_dc_restore.nii.gz
    --hcp_prefs_template_res .. The resolution (in mm) of the structural images 
                                templates to use in the prefs step. Note: it should
                                match the resolution of the acquired structural 
                                images.

   
    Gradient Coefficient File Specification:
    ----------------------------------------

    `--hcp_gdcoeffs` parameter can be set to either 'NONE', a path to a specific
    file to use, or a string that describes, which file to use in which case. 
    Each option of the string has to be dividied by a pipe '|' character and it
    has to specify, which information to look up, a possible value, and a file 
    to use in that case, separated by a colon ':' character. The information 
    too look up needs to be present in the description of that session. 
    Standard options are e.g.:

    institution: Yale
    device: Siemens|Prisma|123456

    Where device is formated as <manufacturer>|<model>|<serial number>.

    If specifying a string it also has to include a `default` option, which 
    will be used in the information was not found. An example could be:

    "default:/data/gc1.conf|model:Prisma:/data/gc/Prisma.conf|model:Trio:/data/gc/Trio.conf"

    With the information present above, the file `/data/gc/Prisma.conf` would
    be used.
    

    Full file checking
    ------------------

    If `--hcp_prefs_check` parameter is set to `all` or a specific file, after
    the completion of processing, the command will check whether processing was
    completed successfully by checking against a given file list. If 'all' is 
    specified, `check_PreFreeSurfer.txt` file will be used, which has to be 
    present in the `<subjectsfolder>/subjects/specs` directory. If another 
    strings is given, the command will first check for a presence of a file with 
    such name in the spec folder (see before), and then check if it is a 
    valid path to a file. If a file is found, each line in a file should 
    represent a file or folder that has to be present in the 
    `<session id>/hcp/<session id>` directory. Folders should be separated by
    lines. Where a session id should be used, `{sessionid}` should be placed. It
    will be replaced with an actual session id at the time of checking. 

    A line that starts with a '#' is considered a comment and will be ignored. 
    If two alternatives are possible and either one of them satisfies the check,
    they should be placed on the same line, separated by a '|' character.

    Example content:
    
    ```
    T1w
    T1w T1w_acpc_dc.nii.gz
    T1w T2w_acpc_dc.nii.gz
    T1w T1w_acpc_brain_mask.nii.gz | T1w T1w_acpc_mask.nii.gz
    ```

    If full file checking is used:

    1/ the success of the run will be judged by the presence of all the files 
       as they are specified in the check file.
    2/ logs will be named:
       done        - the final file is present as well as all the required files
       incomplete  - the final file is present but not all the required files
       error       - the final file is missing
    3/ missing files will be printed to the stdout and a full report will be 
       appended to the log file.


    EXAMPLE USE
    ===========
    
    ```
    qunex hcp_PreFS sessions=fcMRI/subjects_hcp.txt subjectsfolder=subjects \\
          overwrite=no cores=10 hcp_brainsize=170
    ```

    ```
    qunex hcp1 sessions=fcMRI/subjects.hcp.txt subjectsfolder=subjects \\
          overwrite=no cores=10 hcp_t2=NONE
    ```

    ----------------
    Written by Grega Repovš

    Changelog
    2017-01-08 Grega Repovš
             - Updated documentation.
    2017-08-17 Grega Repovš
             - Added checking for field map images.
    2018-12-14 Grega Repovš
             - Cleaned up 
    2019-01-16 Grega Repovš
             - HCP Pipelines compatible
    2019-04-25 Grega Repovš
             - Changed subjects to sessions
    2019-05-22 Grega Repovš
             - Added reading individual image parameters and matching SE images
    2019-05-24 Grega Repovš
             - Added support for v2 folder structure
    2019-05-26 Grega Repovš
             - Updated and simplified
             - Added full file checking
    2019-05-31 Grega Repovš
             - Updated target check image
    2019-06-06 Grega Repovš
             - Enabled multiple log file locations
    2019-10-20 Grega Repovš
             - Adjusted parameters, help and processing to use integrated HCPpipelines
    2020-01-05 Grega Repovš
             - Updated documentation
    2020-01-16 Grega Repovš
             - Updated documentation on SE label specification
    '''

    r = "\n---------------------------------------------------------"
    r += "\nSession id: %s \n[started on %s]" % (sinfo['id'], datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))
    r += "\n%s HCP PreFreeSurfer Pipeline [%s] ...\n" % (action("Running", options['run']), options['hcp_processing_mode'])

    run    = True
    report = "Error"

    try:

        doOptionsCheck(options, sinfo, 'hcp_PreFS')
        doHCPOptionsCheck(options, sinfo, 'hcp_PreFS')
        hcp = getHCPPaths(sinfo, options)

        # --- checks

        if 'hcp' not in sinfo:
            r += "\n---> ERROR: There is no hcp info for session %s in batch.txt" % (sinfo['id'])
            run = False

        # --- check for T1w and T2w images

        for tfile in hcp['T1w'].split("@"):
            if os.path.exists(tfile):
                r += "\n---> T1w image file present."
                T1w = [v for (k, v) in sinfo.iteritems() if k.isdigit() and v['name'] == 'T1w'][0]
                if 'DwellTime' in T1w:
                    options['hcp_t1samplespacing'] = T1w['DwellTime']
                    r += "\n---> T1w image specific EchoSpacing: %s s" % (options['hcp_t1samplespacing'])
                elif 'EchoSpacing' in T1w:
                    options['hcp_t1samplespacing'] = T1w['EchoSpacing']
                    r += "\n---> T1w image specific EchoSpacing: %s s" % (options['hcp_t1samplespacing'])
                if 'UnwarpDir' in T1w:
                    options['hcp_unwarpdir'] = T1w['UnwarpDir']
                    r += "\n---> T1w image specific unwarp direction: %s" % (options['hcp_unwarpdir'])
            else:
                r += "\n---> ERROR: Could not find T1w image file. [%s]" % (tfile)
                run = False

        if hcp['T2w'] in ['', 'NONE']:
            if options['hcp_processing_mode'] == 'HCPStyleData':
                r += "\n---> ERROR: The requested HCP processing mode is 'HCPStyleData', however, no T2w image was specified!\n            Consider using LegacyStyleData processing mode."
                run = False
            else:
                r += "\n---> Not using T2w image."
        else:
            for tfile in hcp['T2w'].split("@"):
                if os.path.exists(tfile):
                    r += "\n---> T2w image file present."
                    T2w = [v for (k, v) in sinfo.iteritems() if k.isdigit() and v['name'] == 'T2w'][0]
                    if 'DwellTime' in T2w:
                        options['hcp_t2samplespacing'] = T2w['DwellTime']
                        r += "\n---> T2w image specific EchoSpacing: %s s" % (options['hcp_t2samplespacing'])
                    elif 'EchoSpacing' in T2w:
                        options['hcp_t2samplespacing'] = T2w['EchoSpacing']
                        r += "\n---> T2w image specific EchoSpacing: %s s" % (options['hcp_t2samplespacing'])
                else:
                    r += "\n---> ERROR: Could not find T2w image file. [%s]" % (tfile)
                    run = False

        # --- do we need spinecho images

        sepos       = ''
        seneg       = ''
        topupconfig = ''
        senum       = None
        tufolder    = None

        if options['hcp_avgrdcmethod'] == 'TOPUP':

            sesettings = True
            for p in ['hcp_sephaseneg', 'hcp_sephasepos', 'hcp_seunwarpdir']:
                if not options[p]:
                    r += '\n---> ERROR: %s parameter is not set! Please review parameter file!' % (p)
                    run = False
                    sesettings = False

            try:
                T1w = [v for (k, v) in sinfo.iteritems() if k.isdigit() and v['name'] == 'T1w'][0]
                senum = T1w.get('se', None)
                if senum:
                    try:
                        senum = int(senum)
                        if senum > 0:
                            tufolder = os.path.join(hcp['source'], 'SpinEchoFieldMap%d%s' % (senum, options['fctail']))
                            r += "\n---> TOPUP Correction, Spin-Echo pair %d specified" % (senum)
                        else:
                            r += "\n---> ERROR: No Spin-Echo image pair specfied for T1w image! [%d]" % (senum)
                            run = False
                    except:                        
                        r += "\n---> ERROR: Could not process the specified Spin-Echo information [%s]! " % (str(senum))
                        run = False

            except:
                pass

            if senum is None:
                try:
                    tufolder = glob.glob(os.path.join(hcp['source'], 'SpinEchoFieldMap*'))
                    tufolder = tufolder[0]
                    senum = int(os.path.basename(tufolder).replace('SpinEchoFieldMap', '').replace('_fncb', ''))
                    r += "\n---> TOPUP Correction, no Spin-Echo pair explicitly specified, using pair %d" % (senum)
                except:
                    r += "\n---> ERROR: Could not find folder with files for TOPUP processing of session %s." % (sinfo['id'])
                    run = False
                    raise
            
            if tufolder and sesettings:
                try:
                    sepos = glob.glob(os.path.join(tufolder, "*_" + options['hcp_sephasepos'] + "*"))[0]
                    seneg = glob.glob(os.path.join(tufolder, "*_" + options['hcp_sephaseneg'] + "*"))[0]

                    if all([sepos, seneg]):
                        r += "\n---> Spin-Echo pair of images present. [%s]" % (os.path.basename(tufolder))
                    else:
                        r += "\n---> ERROR: Could not find the relevant Spin-Echo files! [%s]" % (tufolder)
                        run = False


                    # get SE info from sesssion info
                    try:
                        seInfo = [v for (k, v) in sinfo.iteritems() if k.isdigit() and 'SE-FM' in v['name'] and 'se' in v and v['se'] == str(senum)][0]
                    except:
                        seInfo = None

                    if seInfo and 'EchoSpacing' in seInfo:
                        options['hcp_seechospacing'] = seInfo['EchoSpacing']
                        r += "\n---> Spin-Echo images specific EchoSpacing: %s s" % (options['hcp_seechospacing'])
                    if seInfo and 'phenc' in seInfo:
                        options['hcp_seunwarpdir'] = SEDirMap[seInfo['phenc']]
                        r += "\n---> Spin-Echo unwarp direction: %s" % (options['hcp_seunwarpdir'])

                    if options['hcp_topupconfig'] != 'NONE' and options['hcp_topupconfig']:
                        topupconfig = options['hcp_topupconfig']
                        if not os.path.exists(options['hcp_topupconfig']):
                            topupconfig = os.path.join(hcp['hcp_Config'], options['hcp_topupconfig'])
                            if not os.path.exists(topupconfig):
                                r += "\n---> ERROR: Could not find TOPUP configuration file: %s." % (options['hcp_topupconfig'])
                                run = False
                            else:
                                r += "\n---> TOPUP configuration file present."
                        else:
                            r += "\n---> TOPUP configuration file present."
                except:
                    r += "\n---> ERROR: Could not find files for TOPUP processing of session %s." % (sinfo['id'])
                    run = False    
                    raise

        elif options['hcp_avgrdcmethod'] == 'GeneralElectricFieldMap':
            if os.path.exists(hcp['fmapge']):
                r += "\n---> Gradient Echo Field Map file present."
            else:
                r += "\n---> ERROR: Could not find Gradient Echo Field Map file for session %s.\n            Expected location: %s" % (sinfo['id'], hcp['fmapge'])
                run = False

        elif options['hcp_avgrdcmethod'] in ['FIELDMAP', 'SiemensFieldMap']:
            if os.path.exists(hcp['fmapmag']):
                r += "\n---> Magnitude Field Map file present."
            else:
                r += "\n---> ERROR: Could not find Magnitude Field Map file for session %s.\n            Expected location: %s" % (sinfo['id'], hcp['fmapmag'])
                run = False
            if os.path.exists(hcp['fmapphase']):
                r += "\n---> Phase Field Map file present."
            else:
                r += "\n---> ERROR: Could not find Phase Field Map file for session %s.\n            Expected location: %s" % (sinfo['id'], hcp['fmapphase'])
                run = False

        else:
            r += "\n---> WARNING: No distortion correction method specified."

        # --- lookup gdcoeffs file if needed

        gdcfile, r, run = checkGDCoeffFile(options['hcp_gdcoeffs'], hcp=hcp, sinfo=sinfo, r=r, run=run)

        # --- see if we have set up to use custom mask

        if options['hcp_prefs_custombrain'] == 'MASK':
            tfile = os.path.join(hcp['T1w_folder'], 'T1w_acpc_dc_restore_brain.nii.gz')
            mfile = os.path.join(hcp['T1w_folder'], 'custom_acpc_dc_restore_mask.nii.gz')
            r += "\n---> Set to run only final atlas registration with a custom mask."

            if os.path.exists(tfile):
                r += "\n     ... Previous results present."
                if os.path.exists(mfile):
                    r += "\n     ... Custom mask present."
                else:
                    r += "\n     ... ERROR: Custom mask missing! [%s]!." % (mfile)
                    run = False
            else:
                run = False
                r += "\n     ... ERROR: No previous results found! Please run PreFS without hcp_prefs_custombrain set to MASK first!"
                if os.path.exists(mfile):
                    r += "\n     ... Custom mask present."
                else:
                    r += "\n     ... ERROR: Custom mask missing as well! [%s]!." % (mfile)

        # --- check if we are using a custom brain

        if options['hcp_prefs_custombrain'] == 'CUSTOM':
            t1files = ['T1w_acpc_dc_restore_brain.nii.gz', 'T1w_acpc_dc_restore.nii.gz']
            t2files = ['T2w_acpc_dc_restore_brain.nii.gz', 'T2w_acpc_dc_restore.nii.gz']
            if hcp['T2w'] in ['', 'NONE']:
                tfiles = t1files
            else:
                tfiles = t1files + t2files

            r += "\n---> Set to run only final atlas registration with custom brain images."

            missingfiles = [] 
            for tfile in tfiles:
                if not os.path.exists(os.path.join(hcp['T1w_folder'], tfile)):
                    missingfiles.append(tfile)

            if missingfiles:
                run = False
                r += "\n     ... ERROR: The following brain files are missing in %s:" % (hcp['T1w_folder'])
                for tfile in missingfiles:
                    r += "\n                %s" % tfile


        # --- Set up the command

        comm = os.path.join(hcp['hcp_base'], 'PreFreeSurfer', 'PreFreeSurferPipeline.sh') + " "

        elements = [("path", sinfo['hcp']), 
                    ('subject', sinfo['id'] + options['hcp_suffix']),
                    ('t1', hcp['T1w']),
                    ('t2', hcp['T2w']),
                    ('t1template', os.path.join(hcp['hcp_Templates'], 'MNI152_T1_%smm.nii.gz' % (options['hcp_prefs_template_res']))),
                    ('t1templatebrain', os.path.join(hcp['hcp_Templates'], 'MNI152_T1_%smm_brain.nii.gz' % (options['hcp_prefs_template_res']))),
                    ('t1template2mm', os.path.join(hcp['hcp_Templates'], 'MNI152_T1_2mm.nii.gz')),
                    ('t2template', os.path.join(hcp['hcp_Templates'], 'MNI152_T2_%smm.nii.gz' % (options['hcp_prefs_template_res']))),
                    ('t2templatebrain', os.path.join(hcp['hcp_Templates'], 'MNI152_T2_%smm_brain.nii.gz' % (options['hcp_prefs_template_res']))),
                    ('t2template2mm', os.path.join(hcp['hcp_Templates'], 'MNI152_T2_2mm.nii.gz')),
                    ('templatemask', os.path.join(hcp['hcp_Templates'], 'MNI152_T1_%smm_brain_mask.nii.gz' % (options['hcp_prefs_template_res']))),
                    ('template2mmmask', os.path.join(hcp['hcp_Templates'], 'MNI152_T1_2mm_brain_mask_dil.nii.gz')),
                    ('brainsize', options['hcp_brainsize']),
                    ('fnirtconfig', os.path.join(hcp['hcp_Config'], 'T1_2_MNI152_2mm.cnf')),
                    ('fmapmag', hcp['fmapmag']),
                    ('fmapphase', hcp['fmapphase']),
                    ('fmapgeneralelectric', hcp['fmapge']),
                    ('echodiff', options['hcp_echodiff']),
                    ('SEPhaseNeg', seneg),
                    ('SEPhasePos', sepos),
                    ('seechospacing', options['hcp_seechospacing']),
                    ('seunwarpdir', options['hcp_seunwarpdir']),
                    ('t1samplespacing', options['hcp_t1samplespacing']),
                    ('t2samplespacing', options['hcp_t2samplespacing']),
                    ('unwarpdir', options['hcp_unwarpdir']),
                    ('gdcoeffs', gdcfile),
                    ('avgrdcmethod', options['hcp_avgrdcmethod']),
                    ('topupconfig', topupconfig),
                    ('bfsigma', options['hcp_bfsigma']),
                    ('printcom', options['hcp_printcom']),
                    ('custombrain', options['hcp_prefs_custombrain']),
                    ('processing-mode', options['hcp_processing_mode'])]

        comm += " ".join(['--%s="%s"' % (k, v) for k, v in elements if v])

        # -- Test files

        tfile = os.path.join(hcp['hcp_nonlin'], 'T1w_restore_brain.nii.gz')
        if hcp['hcp_prefs_check']:
            fullTest = {'tfolder': hcp['base'], 'tfile': hcp['hcp_prefs_check'], 'fields': [('sessionid', sinfo['id'])], 'specfolder': options['specfolder']}
        else:
            fullTest = None

        # -- Run

        if run:
            if options['run'] == "run":
                if overwrite and os.path.exists(tfile):
                    os.remove(tfile)

                r, endlog, report, failed = runExternalForFile(tfile, comm, 'Running HCP PreFS', overwrite=overwrite, thread=sinfo['id'], remove=options['log'] == 'remove', task=options['command_ran'], logfolder=options['comlogs'], logtags=options['logtag'], fullTest=fullTest, shell=True, r=r)

            # -- just checking
            else:
                passed, report, r, failed = checkRun(tfile, fullTest, 'HCP PreFS', r)
                if passed is None:
                    r += "\n---> HCP PreFS can be run"
                    report = "HCP Pre FS can be run"
                    failed = 0
                r += "\n-----------------------------------------------------\nCommand to run:\n %s\n-----------------------------------------------------\n" % (comm.replace("--", "\n    --"))
        else:
            r += "\n---> Due to missing files session can not be processed."
            report = "Files missing, PreFS can not be run"
            failed = 1

    except ge.CommandFailed as e:
        r +=  "\n\nERROR in completing %s at %s:\n     %s\n" % ('PreFreeSurfer', e.function, "\n     ".join(e.report))
        report = "PreFS failed"
        failed = 1
    except (ExternalFailed, NoSourceFolder), errormessage:
        r = str(errormessage)
        report = "PreFS failed"
        failed = 1
    except:
        r += "\nERROR: Unknown error occured: \n...................................\n%s...................................\n" % (traceback.format_exc())
        report = "PreFS failed"
        failed = 1

    r += "\nHCP PreFS %s on %s\n---------------------------------------------------------" % (action("completed", options['run']), datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))

    # print r
    return (r, (sinfo['id'], report, failed))


def hcpFS(sinfo, options, overwrite=False, thread=0):
    '''
    hcp_FS [... processing options]
    hcp2 [... processing options]

    USE
    ===

    Runs the FS step of the HCP Pipeline. It takes the T1w and T2w images
    processed in the previous (hcp_PreFS) step, segments T1w image by brain
    matter and CSF, reconstructs the cortical surface of the brain and assigns
    structure labels for both subcortical and cortical structures. It completes
    the listed in multiple steps of increased precision and (if present) uses
    T2w image to refine the surface reconstruction. It uses the adjusted
    version of the HCP code that enables the preprocessing to run also if no T2w
    image is present. A short name 'hcp2' can be used for this command.

    REQUIREMENTS
    ============

    The code expects the previous step (hcp_PreFS) to have run successfully and
    checks for presence of a few key files and folders. Due to the number of
    inputs that it requires, it does not make a full check for all of them!

    RESULTS
    =======

    The results of this step will be present in the above mentioned T1w folder
    as well as MNINonLinear folder in the sessions's root hcp folder.

    RELEVANT PARAMETERS
    ===================

    general parameters
    ------------------

    When running the command, the following *general* processing parameters are
    taken into account:

    --sessions              ... The batch.txt file with all the sessions information
                                [batch.txt].
    --subjectsfolder        ... The path to the study/subjects folder, where the
                                imaging  data is supposed to go [.].
    --cores                 ... How many cores to utilize [1].
    --overwrite             ... Whether to overwrite existing data (yes) or not (no)
                                [no].
    --logfolder             ... The path to the folder where runlogs and comlogs
                                are to be stored, if other than default []
    --log                   ... Whether to keep ('keep') or remove ('remove') the
                                temporary logs once jobs are completed ['keep'].
                                When a comma separated list is given, the log will
                                be created at the first provided location and then 
                                linked or copied to other locations. The valid 
                                locations are: 
                                * 'study'   for the default: 
                                            `<study>/processing/logs/comlogs`
                                            location,
                                * 'session' for `<sessionid>/logs/comlogs
                                * 'hcp'     for `<hcp_folder>/logs/comlogs
                                * '<path>'  for an arbitrary directory
    --hcp_processing_mode   ... Controls whether the HCP acquisition and processing 
                                guidelines should be treated as requirements 
                                (HCPStyleData) or if additional processing 
                                functionality is allowed (LegacyStyleData). In this
                                case running processing w/o a T2w image.
    --hcp_folderstructure   ... Specifies the version of the folder structure to
                                use, 'initial' and 'hcpls' are supported ['hcpls']
    --hcp_filename          ... Specifies whether the standard ('standard') filenames
                                or the specified original names ('original') are to
                                be used ['standard']
    
    specific parameters
    -------------------

    In addition the following *specific* parameters will be used to guide the
    processing in this step:

    --hcp_fs_check    ... Whether to check the results of FreeSurfer  pipeline 
                          by presence of last file generated  ('last'), the 
                          default list of all files ('all') or using a specific
                          check file ('<path to file>'). ['last']


    HCP Pipelines specific parameters
    ---------------------------------

    These are optional parameters. Please note that they will only be used
    when HCP Pipelines are used. They are not implemented in hcpmodified!
    
    --hcp_fs_seed             ... Recon-all seed value. If not specified, none
                                  will be used. []
    --hcp_fs_existing_subject ... Indicates that the command is to be run on
                                  top of an already existing analysis/subject.
                                  This excludes the `-i` flag from the 
                                  invocation of recon-all. If set, the
                                  user needs to specify which recon-all stages
                                  to run using the --hcp_fs_extra_reconall
                                  parameter. Accepted values are TRUE and 
                                  FALSE [FALSE]
    --hcp_fs_extra_reconall   ... A string with extra parameters to pass to 
                                  FreeSurfer recon-all. The extra parameters are
                                  to be listed in a pipe ('|') separated string. 
                                  Parameters and their values need to be listed
                                  separately. E.g. to pass `-norm3diters 3` to 
                                  reconall, the string has to be: 
                                  "-norm3diters|3" []
    --hcp_fs_flair            ... If set to TRUE indicates that recon-all is to be
                                  run with the -FLAIR/-FLAIRpial options
                                  (rather than the -T2/-T2pial options).
                                  The FLAIR input image itself should be provided 
                                  as a regular T2w image.

    HCP LegacyStyleData processing mode parameters:
    -----------------------------------------------

    Please note, that these settings will only be used when LegacyStyleData 
    processing mode is specified!


    --hcp_suffix            ... Specifies a suffix to the session id if multiple
                                variants are run, empty otherwise [].
    --hcp_t2                ... NONE if no T2w image is available and the
                                preprocessing should be run without them,
                                anything else otherwise [t2]. NONE is only valid
                                if 'LegacyStyleData' processing mode was specified.
    --hcp_expert_file       ... Path to the read-in expert options file for
                                FreeSurfer if one is prepared and should be used
                                empty otherwise [].
    *--hcp_control_points   ... Specify YES to use manual control points or
                                empty otherwise [].
    *--hcp_wm_edits         ... Specify YES to use manually edited WM mask or
                                empty otherwise [].
    *--hcp_fs_brainmask     ... Specify 'original' to keep the masked original 
                                brain image; 'manual' to use the manually edited
                                brainmask file; default 'fs' uses the brainmask 
                                generated by mri_watershed [fs].
    *--hcp_autotopofix_off  ... Specify YES to turn off the automatic topologic 
                                fix step in FS and compute WM surface 
                                deterministically from manual WM mask, or empty 
                                otherwise [].                             
    --hcp_freesurfer_home   ... Path for FreeSurfer home folder can be manually
                                specified to override default environment 
                                variable to ensure backwards compatiblity and 
                                hcp2 customization.

    * these options are currently not available

    Full file checking
    ------------------

    If `--hcp_prefs_check` parameter is set to `all` or a specific file, after
    the completion of processing, the command will check whether processing was
    completed successfully by checking against a given file list. If 'all' is 
    specified, `check_PreFreeSurfer.txt` file will be used, which has to be 
    present in the `<subjectsfolder>/subjects/specs` directory. If another 
    strings is given, the command will first check for a presence of a file with 
    such name in the spec folder (see before), and then check if it is a 
    valid path to a file. If a file is found, each line in a file should 
    represent a file or folder that has to be present in the 
    `<session id>/hcp/<session id>` directory. Folders should be separated by
    lines. Where a session id should be used, `{sessionid}` should be placed. It
    will be replaced with an actual session id at the time of checking. 

    A line that starts with a '#' is considered a comment and will be ignored. 
    If two alternatives are possible and either one of them satisfies the check,
    they should be placed on the same line, separated by a '|' character.

    Example content:
    
    ```
    T1w
    T1w T1w_acpc_dc.nii.gz
    T1w T2w_acpc_dc.nii.gz
    T1w T1w_acpc_brain_mask.nii.gz | T1w T1w_acpc_mask.nii.gz
    ```

    If full file checking is used:

    1/ the success of the run will be judged by the presence of all the files 
       as they are specified in the check file.
    2/ logs will be named:
       done        - the final file is present as well as all the required files
       incomplete  - the final file is present but not all the required files
       error       - the final file is missing
    3/ missing files will be printed to the stdout and a full report will be 
       appended to the log file.



    EXAMPLE USE
    ===========
    

    ```
    qunex hcp_FS sessions=fcMRI/subjects.hcp.txt subjectsfolder=subjects \\
          overwrite=no cores=10
    ```

    ```
    qunex hcp_FS sessions=fcMRI/subjects.hcp.txt subjectsfolder=subjects \\
          overwrite=no cores=10 hcp_fs_longitudinal=TemplateA
    ```

    ```
    qunex hcp2 sessions=fcMRI/subjects.hcp.txt subjectsfolder=subjects \\
          overwrite=no cores=10 hcp_t2=NONE
    ```

    ```
    qunex hcp2 sessions=fcMRI/subjects.hcp.txt subjectsfolder=subjects \\
          overwrite=no cores=10 hcp_t2=NONE \\
          hcp_freesurfer_home=<absolute_path_to_freesurfer_binary> \\
    ```

    ----------------
    Written by Grega Repovš

    Changelog
    2017-01-08 Grega Repovš
             - Updated documentation.
    2017-03-19 Alan Anticevic
             - Updated documentation.
    2017-03-20 Alan Anticevic
             - Updated documentation.
    2018-05-05 Grega Repovš
             - Optimized version checking.
    2018-12-09 Grega Repovš
             - Integrated changes from Lisa Ji
             - Optimized folder construction
             - Adapted removal of preexisting data for longitudinal run
    2018-12-14 Grega Repovš
             - Cleaned up, updated documentation
    2019-01-12 Grega Repovš
             - Cleaned up furher, added updates by Lisa Ji
    2019-01-16 Grega Repovš
             - Added HCP Pipelines options
    2019-04-25 Grega Repovš
             - Changed subjects to sessions
    2019-05-26 Grega Repovš
             - Updated and simplified
             - Made compatible with latest HCP code
             - Added full file checking
    2019-06-06 Grega Repovš
             - Enabled multiple log file locations
    2019-10-20 Grega Repovš
             - Adjusted parameters, help and processing to use integrated HCPpipelines
    2019-10-24 Grega Repovš
             - Added flair option and documentation
    2020-01-05 Grega Repovš
             - Updated documentation

    ----------------
    2019-10-20 ToDo
             - Adjust code to enable running with FreeSurfer 5.3-HCP
             - Enable longitudinal mode
             - Enable using additional parameters
                -> hcp_control_points
                -> hcp_wm_edits
                -> hcp_fs_brainmask
                -> hcp_autotopofix_off
    '''

    r = "\n---------------------------------------------------------"
    r += "\nSession id: %s \n[started on %s]" % (sinfo['id'], datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))
    r += "\n\n%s HCP FreeSurfer Pipeline [%s] ...\n" % (action("Running", options['run']), options['hcp_processing_mode'])

    run    = True
    status = True
    report = "Error"

    try:
        doOptionsCheck(options, sinfo, 'hcp_FS')
        doHCPOptionsCheck(options, sinfo, 'hcp_FS')
        hcp = getHCPPaths(sinfo, options)

        # --- run checks

        if 'hcp' not in sinfo:
            r += "\n---> ERROR: There is no hcp info for session %s in batch.txt" % (sinfo['id'])
            run = False
      
        # -> Pre FS results

        if os.path.exists(os.path.join(hcp['T1w_folder'], 'T1w_acpc_dc_restore_brain.nii.gz')):
            r += "\n---> PreFS results present."
        else:
            r += "\n---> ERROR: Could not find PreFS processing results."
            run = False

        # -> T2w image

        if hcp['T2w'] in ['', 'NONE']:
            t2w = 'NONE'
        else:
            t2w = os.path.join(hcp['T1w_folder'], 'T2w_acpc_dc_restore.nii.gz')

        if t2w == 'NONE' and options['hcp_processing_mode'] == 'HCPStyleData':
            r += "\n---> ERROR: The requested HCP processing mode is 'HCPStyleData', however, not T2w image was specified!\n            Consider using LegacyStyleData processing mode."
            run = False

        # -> check version of FS against previous version of FS

        # ------------------------------------------------------------------
        # - Alan added integrated code for FreeSurfer 6.0 completion check
        # -----------------------------------------------------------------

        freesurferhome = options['hcp_freesurfer_home']

        # - Set FREESURFER_HOME based on --hcp_freesurfer_home flag to ensure backward compatibility
        if freesurferhome:
            sys.path.append(freesurferhome)
            os.environ['FREESURFER_HOME'] = str(freesurferhome)
            r +=  "\n---> FREESURFER_HOME set to: " + str(freesurferhome)
            versionfile = os.path.join(os.environ['FREESURFER_HOME'], 'build-stamp.txt')
        else:
            fshome = os.environ["FREESURFER_HOME"]
            r += "\n---> FREESURFER_HOME set to: " + str(fshome)
            versionfile = os.path.join(os.environ['FREESURFER_HOME'], 'build-stamp.txt')

        fsbuildstamp = open(versionfile).read()

        for fstest, fsversion in [('stable-pub-v6.0.0', '6.0'), ('stable-pub-v5.3.0-HCP', '5.3-HCP'), ('unknown', 'unknown')]:
            if fstest in fsbuildstamp:
                break

        # - Check if recon-all.log exists to set the FS version
        reconallfile = os.path.join(hcp['T1w_folder'], sinfo['id'] + options['hcp_suffix'], 'scripts', 'recon-all.log')

        if os.path.exists(reconallfile):
            r +=  "\n---> Existing FreeSurfer recon-all.log was found!"

            reconallfiletxt = open(reconallfile).read()
            for fstest, efsversion in [('stable-pub-v6.0.0', '6.0'), ('stable-pub-v5.3.0-HCP', '5.3-HCP'), ('unknown', 'unknown')]:
                if fstest in reconallfiletxt:
                    break

            if overwrite and options['run'] == "run":
                r += "\n     ... removing previous files"
            else:
                if fsversion == efsversion:
                    r += "\n     ... current FREESURFER_HOME settings match previous version of recon-all.log [%s]." % (fsversion)
                    r += "\n         Proceeding ..."
                else:
                    r += "\n     ... ERROR: current FREESURFER_HOME settings [%s] do not match previous version of recon-all.log [%s]!" % (fsversion, efsversion)
                    r += "\n         Please check your FS version or set overwrite to yes"
                    run = False

        # --- set target file

        # --- Deprecated versions of tfile variable based on prior FS runs ---------------------------------------------
        # tfile = os.path.join(hcp['T1w_folder'], sinfo['id'] + options['hcp_suffix'], 'mri', 'aparc+aseg.mgz')
        # tfile = os.path.join(hcp['T1w_folder'], '_FS.done')
        # tfile = os.path.join(hcp['T1w_folder'], sinfo['id'] + options['hcp_suffix'], 'label', 'BA_exvivo.thresh.ctab')
        # --------------------------------------------------------------------------------------------------------------

        tfiles = {'6.0':     os.path.join(hcp['FS_folder'], 'label', 'BA_exvivo.thresh.ctab'),
                  '5.3-HCP': os.path.join(hcp['FS_folder'], 'label', 'rh.entorhinal_exvivo.label')}
        tfile = tfiles[fsversion]

        
        # --> longitudinal run currently not supported
        #
        # identify template if longitudinal run
        #
        # fslongitudinal = ""
        #
        # if options['hcp_fs_longitudinal']:
        #     if 'subject' not in sinfo:
        #         r += "\n     ... 'subject' field not defined in batch file, can not run longitudinal FS"
        #         run = False
        #     elif sinfo['subject'] == sinfo['id']:
        #         r += "\n     ... 'subject' field is equal to session 'id' field, can not run longitudinal FS"
        #         run = False
        #     else:
        #         lresults = os.path.join(hcp['FS_long_template'], 'label', 'rh.entorhinal_exvivo.label')                
        #         if not os.path.exists(lresults):
        #             r += "\n     ... ERROR: Longitudinal template not present! [%s]" % (lresults)
        #             r += "\n                Please chesk the results of longitudinalFS command!"
        #             r += "\n                Please check your data and settings!" % (lresults)
        #             run = False   
        #         else:
        #             r += "\n     ... longitudinal template present"
        #             fslongitudinal = "run"
        #             tfiles = {'6.0':     os.path.join(hcp['FS_long_results'], 'label', 'BA_exvivo.thresh.ctab'),
        #                       '5.3-HCP': os.path.join(hcp['FS_long_results'], 'label', 'rh.entorhinal_exvivo.label')}
        #             tfile = tfiles[fsversion]
        
        # --> Building the command string
 
        comm = os.path.join(hcp['hcp_base'], 'FreeSurfer', 'FreeSurferPipeline.sh') + " "

        # -> Key elements

        elements = [("subjectDIR",       hcp['T1w_folder']), 
                    ('subject',          sinfo['id'] + options['hcp_suffix']),
                    ('t1',               os.path.join(hcp['T1w_folder'], 'T1w_acpc_dc_restore.nii.gz')),
                    ('t1brain',          os.path.join(hcp['T1w_folder'], 'T1w_acpc_dc_restore_brain.nii.gz')),
                    ('t2',               t2w),
                    ('seed',             options['hcp_fs_seed']),                    
                    ('no-conf2hires',    options['hcp_fs_no_conf2hires']),                    
                    ('processing-mode',  options['hcp_processing_mode'])]

        # -> Additional, reconall parameters

        if options['hcp_fs_extra_reconall']:
            for f in options['hcp_fs_extra_reconall'].split('|'):
                elements.append(('extra-reconall-arg', f))

        # -> additional Qu|Nex passed parameters

        if options['hcp_expert_file']:
            elements.append(('extra-reconall-arg', '-expert'))
            elements.append(('extra-reconall-arg', options['hcp_expert_file']))
            
        # --> Pull all together

        comm += " ".join(['--%s="%s"' % (k, v) for k, v in elements if v])

        # --> Add flags

        for optionName, flag in [('hcp_fs_flair', '--flair'), ('hcp_fs_existing_subject', '--existing-subject')]:
            if options[optionName]:
                comm += " %s" % (flag)

        # -- Test files

        if hcp['hcp_fs_check']:
            fullTest = {'tfolder': hcp['base'], 'tfile': hcp['hcp_fs_check'], 'fields': [('sessionid', sinfo['id'])], 'specfolder': options['specfolder']}
        else:
            fullTest = None

        # -- Run

        if run:
            if options['run'] == "run":

                # --> clean up test file if overwrite or if hcp_fs_existing_subject is set to True
                if (overwrite and os.path.lexists(tfile)) or (options['hcp_fs_existing_subject'] and os.path.lexists(tfile)):
                    os.remove(tfile)

                # --> clean up only if hcp_fs_existing_subject is not set to True
                if (overwrite or not os.path.exists(tfile)) and not options['hcp_fs_existing_subject']:
                    # -> longitudinal mode currently not supported
                    # if options['hcp_fs_longitudinal']:
                    #     if os.path.lexists(hcp['FS_long_results']):
                    #         r += "\n --> removing preexisting folder with longitudinal results [%s]" % (hcp['FS_long_results'])
                    #         shutil.rmtree(hcp['FS_long_results'])
                    # else:
                        if os.path.lexists(hcp['FS_folder']):
                            r += "\n ---> removing preexisting FS folder [%s]" % (hcp['FS_folder'])
                            shutil.rmtree(hcp['FS_folder'])
                        for toremove in ['fsaverage', 'lh.EC_average', 'rh.EC_average', os.path.join('xfms','OrigT1w2T1w.nii.gz')]:
                            rmtarget = os.path.join(hcp['T1w_folder'], toremove)
                            try:
                                if os.path.islink(rmtarget) or os.path.isfile(rmtarget):
                                    os.remove(rmtarget)
                                elif os.path.isdir(rmtarget):
                                    shutil.rmtree(rmtarget)
                            except:
                                r += "\n---> WARNING: Could not remove preexisting file/folder: %s! Please check your data!" % (rmtarget)
                                status = False
                if status:
                    r, endlog, report, failed = runExternalForFile(tfile, comm, 'Running HCP FS', overwrite=overwrite, thread=sinfo['id'], remove=options['log'] == 'remove', task=options['command_ran'], logfolder=options['comlogs'], logtags=options['logtag'], fullTest=fullTest, shell=True, r=r)

            # -- just checking
            else:
                passed, report, r, failed = checkRun(tfile, fullTest, 'HCP FS', r)
                if passed is None:
                    r += "\n---> HCP FS can be run"
                    report = "HCP FS can be run"
                    failed = 0
                r += "\n-----------------------------------------------------\nCommand to run:\n %s\n-----------------------------------------------------\n" % (comm.replace("--", "\n    --"))
        else:
            r += "\n---> Subject can not be processed."
            report = "FS can not be run"
            failed = 1
    
    except ge.CommandFailed as e:
        r +=  "\n\nERROR in completing %s at %s:\n     %s\n" % ('FreeSurfer', e.function, "\n     ".join(e.report))
        report = "FS failed"
        failed = 1
    except (ExternalFailed, NoSourceFolder), errormessage:
        r = str(errormessage)
        failed = 1
    except:
        r += "\nERROR: Unknown error occured: \n...................................\n%s...................................\n" % (traceback.format_exc())
        failed = 1

    r += "\n\nHCP FS %s on %s\n---------------------------------------------------------" % (action("completed", options['run']), datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))

    # print r
    return (r, (sinfo['id'], report, failed))



def longitudinalFS(sinfo, options, overwrite=False, thread=0):
    '''
    longitudinalFS [... processing options]
    lfs [... processing options]

    USE
    ===

    Runs longitudinal FreeSurfer processing in cases when multiple sessions with
    structural data exist for a single subjects

    REQUIREMENTS
    ============

    The code expects the FreeSurfer Pipeline (hcp_PreFS) to have run 
    successfully on all subject's session. In the batch file, there need to be 
    clear separation between session id (`id` parameter) and and subject id 
    (`subject` parameter). So that the command can identify which sessions 
    belong to which subject

    RESULTS
    =======

    The result is a longitudinal FreeSurfer template that is created in 
    `FSTemplates` folder for each subject in a subfolder with the template name, 
    but is also copied to each session's hcp folder in the T1w folder as
    sessionid.long.TemplateA. An example is shown below:

    study
    └─ subjects
       ├─ subject1_session1
       │  └─ hcp
       │     └─ subject1_session1
       │       └─ T1w
       │          ├─ subject1_session1 (FS folder - original)
       │          └─ subject1_session1.long.TemplateA (FS folder - longitudinal)
       ├─ subject1_session2
       ├─ ...
       └─ FSTemplates
          ├─ subject1
          │  └─ TemplateA
          └─ ...


    RELEVANT PARAMETERS
    ===================

    general parameters
    ------------------

    When running the command, the following *general* processing parameters are
    taken into account:

    --sessions        ... The batch.txt file with all the sessions information
                          [batch.txt].
    --subjectsfolder  ... The path to the study/subjects folder, where the
                          imaging data is supposed to go [.].
    --cores           ... How many cores to utilize [1].
    --overwrite       ... Whether to overwrite existing data (yes) or not (no)
                          [no].
    --logfolder       ... The path to the folder where runlogs and comlogs
                          are to be stored, if other than default []
    --log             ... Whether to keep ('keep') or remove ('remove') the
                          temporary logs once jobs are completed ['keep'].
                          When a comma separated list is given, the log will
                          be created at the first provided location and then 
                          linked or copied to other locations. The valid 
                          locations are: 
                          * 'study'   for the default: 
                                      `<study>/processing/logs/comlogs`
                                      location,
                          * 'session' for `<sessionid>/logs/comlogs
                          * 'hcp'     for `<hcp_folder>/logs/comlogs
                          * '<path>'  for an arbitrary directory

    --hcp_folderstructure   ... Specifies the version of the folder structure to
                                use, 'initial' and 'hcpls' are supported ['hcpls']
    --hcp_filename          ... Specifies whether the standard ('standard') filenames
                                or the specified original names ('original') are to
                                be used ['standard']

    specific parameters
    -------------------

    In addition the following *specific* parameters will be used to guide the
    processing in this step:

    --hcp_suffix            ... Specifies a suffix to the session id if multiple
                                variants are run, empty otherwise [].
    --hcp_t2                ... NONE if no T2w image is available and the
                                preprocessing should be run without them,
                                anything else otherwise [t2].
    --hcp_expert_file       ... Path to the read-in expert options file for
                                FreeSurfer if one is prepared and should be used
                                empty otherwise [].
    --hcp_control_points    ... Specify YES to use manual control points or
                                empty otherwise [].
    --hcp_wm_edits          ... Specify YES to use manually edited WM mask or
                                empty otherwise [].
    --hcp_fs_brainmask      ... Specify 'original' to keep the masked original 
                                brain image; 'manual' to use the manually edited
                                brainmask file; default 'fs' uses the brainmask 
                                generated by mri_watershed [fs].
    --hcp_autotopofix_off   ... Specify YES to turn off the automatic topologic 
                                fix step in FS and compute WM surface 
                                deterministically from manual WM mask, or empty 
                                otherwise [].                             
    --hcp_freesurfer_home   ... Path for FreeSurfer home folder can be manually
                                specified to override default environment 
                                variable to ensure backwards compatiblity and 
                                hcp2 customization.
    --hcp_freesurfer_module ... Whether to load FreeSurfer as a module on the 
                                cluster. You can specify using YES or empty 
                                otherwise []. To ensure backwards compatiblity 
                                and hcp2 customization.
    --hcp_fs_longitudinal   ... The name of the FS longitudinal template to
                                be used for the template resulting from this 
                                command call.
    --hcp_fslong_check      ... Whether to check the results of FSLongitudinal 
                                pipeline by presence of last file generated 
                                ('last'), the default list of all files ('all') 
                                or using a specific check file ('<path to file>')
                                ['last']
    
    Full file checking
    ------------------

    If `--hcp_prefs_check` parameter is set to `all` or a specific file, after
    the completion of processing, the command will check whether processing was
    completed successfully by checking against a given file list. If 'all' is 
    specified, `check_PreFreeSurfer.txt` file will be used, which has to be 
    present in the `<subjectsfolder>/subjects/specs` directory. If another 
    strings is given, the command will first check for a presence of a file with 
    such name in the spec folder (see before), and then check if it is a 
    valid path to a file. If a file is found, each line in a file should 
    represent a file or folder that has to be present in the 
    `<session id>/hcp/<session id>` directory. Folders should be separated by
    lines. Where a session id should be used, `{sessionid}` should be placed. It
    will be replaced with an actual session id at the time of checking. 

    A line that starts with a '#' is considered a comment and will be ignored. 
    If two alternatives are possible and either one of them satisfies the check,
    they should be placed on the same line, separated by a '|' character.

    Example content:
    
    ```
    T1w
    T1w T1w_acpc_dc.nii.gz
    T1w T2w_acpc_dc.nii.gz
    T1w T1w_acpc_brain_mask.nii.gz | T1w T1w_acpc_mask.nii.gz
    ```

    If full file checking is used:

    1/ the success of the run will be judged by the presence of all the files 
       as they are specified in the check file.
    2/ logs will be named:
       done        - the final file is present as well as all the required files
       incomplete  - the final file is present but not all the required files
       error       - the final file is missing
    3/ missing files will be printed to the stdout and a full report will be 
       appended to the log file.


    EXAMPLE USE
    ===========
    
    ```
    qunex longitudinalFS sessions=fcMRI/subjects.hcp.txt subjectsfolder=subjects \\
          overwrite=no cores=10
    ```

    ```
    qunex lfs sessions=fcMRI/subjects.hcp.txt subjectsfolder=subjects \\
          overwrite=no cores=10 hcp_t2=NONE
    ```

    ```
    qunex lsf sessions=fcMRI/subjects.hcp.txt subjectsfolder=subjects \\
          overwrite=no cores=10 hcp_t2=NONE \\
          hcp_freesurfer_home=<absolute_path_to_freesurfer_binary> \\
          hcp_freesurfer_module=YES
    ```

    ----------------
    Written by Grega Repovš

    Changelog
    2018-09-14 Grega Repovš
             - Initial test version
    2018-12-09 Grega Repovš
             - Adjusted paths creation
    2018-12-14 Grega Repovš
             - Updated documentation
    2019-04-25 Grega Repovš
             - Changed subjects to sessions
    2019-05-26 Grega Repovš
             - Updated and simplified
             - Added full file checking
    2019-06-06 Grega Repovš
             - Enabled multiple log file locations
    '''

    r = "\n---------------------------------------------------------"
    r += "\nSubject id: %s \n[started on %s]" % (sinfo['id'], datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))
    r += "\n\n%s Longitudinal FreeSurfer Pipeline [%s] ...\n" % (action("Running", options['run']), options['hcp_processing_mode'])

    run           = True
    report        = "Error"
    sessionsid    = []
    sessionspaths = []
    resultspaths  = []

    try:

        # --- check that we have data for all sessions

        r += "\n---> Checking sessions for subject %s" % (sinfo['id'])

        for session in sinfo['sessions']:
            r += "\n     => session %s" % (session['id'])
            sessionsid.append(session['id'] + options['hcp_suffix'])
            sessionStatus = True

            try:
                doOptionsCheck(options, sinfo, 'longitudinalFS')
                doHCPOptionsCheck(options, sinfo, 'longitudinalFS')
                hcp = getHCPPaths(session, options)
                sessionspaths.append(hcp['FS_folder'])
                resultspaths.append(hcp['FS_long_results'])
                # --- run checks

                if 'hcp' not in session:
                    r += "\n       -> ERROR: There is no hcp info for session %s in batch file" % (session['id'])
                    sessionStatus = False

                # --- check for T1w and T2w images

                for tfile in hcp['T1w'].split("@"):
                    if os.path.exists(tfile):
                        r += "\n       -> T1w image file present."
                    else:
                        r += "\n       -> ERROR: Could not find T1w image file."
                        sessionStatus = False

                if hcp['T2w'] == 'NONE':
                    r += "\n       -> Not using T2w image."
                else:
                    for tfile in hcp['T2w'].split("@"):
                        if os.path.exists(tfile):
                            r += "\n       -> T2w image file present."
                        else:
                            r += "\n       -> ERROR: Could not find T2w image file."
                            sessionStatus = False

                # -> Pre FS results

                if os.path.exists(os.path.join(hcp['T1w_folder'], 'T1w_acpc_dc_restore_brain.nii.gz')):
                    r += "\n       -> PreFS results present."
                else:
                    r += "\n       -> ERROR: Could not find PreFS processing results."
                    sessionStatus = False

                # -> FS results

                if os.path.exists(os.path.join(hcp['FS_folder'], 'mri', 'aparc+aseg.mgz')):
                    r += "\n       -> FS results present."
                else:
                    r += "\n       -> ERROR: Could not find Freesurfer processing results."
                    sessionStatus = False

                if sessionStatus:
                    r += "\n     => data check for session completed successfully!\n"
                else:
                    r += "\n     => data check for session failed!\n"
                    run = False
            except:
                r += "\n     => data check for session failed!\n"

        if run:
            r += "\n===> OK: Sessions check completed with success!"
        else:
            r += "\n===> ERROR: Sessions check failed. Please check your data before proceeding!"

        if hcp['T2w'] == 'NONE':
            t2w = 'NONE'
        else:
            t2w = 'T2w_acpc_dc_restore.nii.gz'
       
        # --- set up command

        comm = '%(script)s \
            --subject="%(subject)s" \
            --subjectDIR="%(subjectDIR)s" \
            --expertfile="%(expertfile)s" \
            --controlpoints="%(controlpoints)s" \
            --wmedits="%(wmedits)s" \
            --autotopofixoff="%(autotopofixoff)s" \
            --fsbrainmask="%(fsbrainmask)s" \
            --freesurferhome="%(freesurferhome)s" \
            --fsloadhpcmodule="%(fsloadhpcmodule)s" \
            --t1="%(t1)s" \
            --t1brain="%(t1brain)s" \
            --t2="%(t2)s" \
            --timepoints="%(timepoints)s" \
            --longitudinal="template"' % {
                'script'            : os.path.join(hcp['hcp_base'], 'FreeSurfer', 'FreeSurferPipeline.sh'),
                'subject'           : options['hcp_fs_longitudinal'],
                'subjectDIR'        : os.path.join(options['subjectsfolder'], 'FSTemplates', sinfo['id']),
                'freesurferhome'    : options['hcp_freesurfer_home'],      # -- Alan added option for --hcp_freesurfer_home flag passing
                'fsloadhpcmodule'   : options['hcp_freesurfer_module'],   # -- Alan added option for --hcp_freesurfer_module flag passing
                'expertfile'        : options['hcp_expert_file'],
                'controlpoints'     : options['hcp_control_points'],
                'wmedits'           : options['hcp_wm_edits'],
                'autotopofixoff'    : options['hcp_autotopofix_off'],
                'fsbrainmask'       : options['hcp_fs_brainmask'],
                't1'                : "",
                't1brain'           : "",
                't2'                : "",
                'timepoints'        : ",".join(sessionspaths)}

       # -- Test files

        if hcp['hcp_fslong_check']:
            fullTest = {'tfolder': hcp['base'], 'tfile': hcp['hcp_fslong_check'], 'fields': [('sessionid', sinfo['id'])], 'specfolder': options['specfolder']}
        else:
            fullTest = None

        # -- Run 

        if run:
            if options['run'] == "run":
                lttemplate = hcp['FS_long_subject_template']
                tfile      = os.path.join(hcp['FS_long_results'], 'label', 'rh.entorhinal_exvivo.label')
                
                if overwrite or not os.path.exists(tfile):
                    try:
                        if os.path.exists(lttemplate):
                            rmfolder = lttemplate
                            shutil.rmtree(lttemplate)
                        for rmfolder in resultspaths:                            
                            if os.path.exists(rmfolder):
                                shutil.rmtree(rmfolder)
                    except:
                        r += "\n---> WARNING: Could not remove preexisting folder: %s! Please check your data!" % (rmfolder)
                        status = False

                    r, endlog, report, failed = runExternalForFile(tfile, comm, 'Running HCP FS Longitudinal', overwrite=overwrite, thread=sinfo['id'], remove=options['log'] == 'remove', task=options['command_ran'], logfolder=options['comlogs'], logtags=options['logtag'], fullTest=fullTest, shell=True, r=r)

            # -- just checking
            else:
                r += "\n---> The command was tested for sessions: %s" % (", ".join(sessionsid))
                r += "\n---> If run, the following command would be executed:\n"
                rcomm = re.sub(r" +", r" ", comm)
                rcomm = re.sub(r"--", r"\n  --", rcomm)
                r += "\n%s\n\n" % rcomm
                report = "Command can be run"
                failed = 0
                
        else:
            r += "\n---> The command could not be run on sessions: %s" % (", ".join(sessionsid))
            r += "\n---> If run, the following command would be executed:\n"
            rcomm = re.sub(r" +", r" ", comm)
            rcomm = re.sub(r"--", r"\n  --", rcomm)
            r += "\n%s\n\n" % rcomm
            report = "Command can not be run"
            failed = 1

    except ge.CommandFailed as e:
        r +=  "\n\nERROR in completing %s at %s:\n     %s\n" % ('FreeSurferLongitudinal', e.function, "\n     ".join(e.report))
        report = "FSLong failed"
        failed = 1
    except (ExternalFailed, NoSourceFolder), errormessage:
        r = str(errormessage)
        failed = 1
    except:
        r += "\nERROR: Unknown error occured: \n...................................\n%s...................................\n" % (traceback.format_exc())
        failed = 1

    r += "\n\nLongitudinal FreeSurfer %s on %s\n---------------------------------------------------------" % (action("completed", options['run']), datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))

    # print r
    return (r, (sinfo['id'], report, failed))



def hcpPostFS(sinfo, options, overwrite=False, thread=0):
    '''
    hcp_PostFS [... processing options]
    hcp3 [... processing options]

    USE
    ===

    Runs the PostFS step of the HCP Pipeline. It creates Workbench compatible
    files based on the Freesurfer segmentation and surface registration. It uses
    the adjusted version of the HCP code that enables the preprocessing to run
    also if no T2w image is present. A short name 'hcp3' can be used for this
    command.

    REQUIREMENTS
    ============

    The code expects the previous step (hcp_FS) to have run successfully and
    checks for presence of the last file that should have been generated. Due
    to the number of files that it requires, it does not make a full check for
    all of them!

    RESULTS
    =======

    The results of this step will be present in the MNINonLinear folder in the
    sessions's root hcp folder.

    RELEVANT PARAMETERS
    ===================

    general parameters
    ------------------

    When running the command, the following *general* processing parameters are
    taken into account:

    --sessions              ... The batch.txt file with all the sessions information
                                [batch.txt].
    --subjectsfolder        ... The path to the study/subjects folder, where the
                                imaging  data is supposed to go [.].
    --cores                 ... How many cores to utilize [1].
    --overwrite             ... Whether to overwrite existing data (yes) or not (no)
                                [no].
    --logfolder             ... The path to the folder where runlogs and comlogs
                                are to be stored, if other than default []
    --log                   ... Whether to keep ('keep') or remove ('remove') the
                                temporary logs once jobs are completed ['keep'].
                                When a comma separated list is given, the log will
                                be created at the first provided location and then 
                                linked or copied to other locations. The valid 
                                locations are: 
                                * 'study'   for the default: 
                                            `<study>/processing/logs/comlogs`
                                            location,
                                * 'session' for `<sessionid>/logs/comlogs
                                * 'hcp'     for `<hcp_folder>/logs/comlogs
                                * '<path>'  for an arbitrary directory
    --hcp_processing_mode   ... Controls whether the HCP acquisition and processing 
                                guidelines should be treated as requirements 
                                (HCPStyleData) or if additional processing 
                                functionality is allowed (LegacyStyleData). In this
                                case running processing w/o a T2w image.
    --hcp_folderstructure   ... Specifies the version of the folder structure to
                                use, 'initial' and 'hcpls' are supported ['hcpls']
    --hcp_filename          ... Specifies whether the standard ('standard') filenames
                                or the specified original names ('original') are to
                                be used ['standard']

    specific parameters
    -------------------

    In addition the following *specific* parameters will be used to guide the
    processing in this step:

    --hcp_suffix            ... Specifies a suffix to the session id if multiple
                                variants are run, empty otherwise [].
    --hcp_t2                ... NONE if no T2w image is available and the
                                preprocessing should be run without them,
                                anything else otherwise [t2]. NONE is only valid
                                if 'LegacyStyleData' processing mode was specified.
    --hcp_grayordinatesres  ... The resolution of the volume part of the
                                graordinate representation in mm [2].
    --hcp_hiresmesh         ... The number of vertices for the high resolution
                                mesh of each hemisphere (in thousands) [164].
    --hcp_lowresmesh        ... The number of vertices for the low resolution
                                mesh of each hemisphere (in thousands) [32].
    --hcp_regname           ... The registration used, FS or MSMSulc [MSMSulc].
    --hcp_mcsigma           ... Correction sigma used for metric smooting [sqrt(200)].
    --hcp_inflatescale      ... Inflate extra scale parameter [1].
    * --hcp_fs_longitudinal ... The name of the FS longitudinal template if one
                                was created and is to be used in this step.
    --hcp_postfs_check      ... Whether to check the results of PreFreeSurfer 
                                pipeline by presence of last file generated 
                                ('last'), the default list of all files ('all') 
                                or using a specific check file ('<path to file>')
                                ['last']

    * this option is currently not available

    Full file checking
    ------------------

    If `--hcp_prefs_check` parameter is set to `all` or a specific file, after
    the completion of processing, the command will check whether processing was
    completed successfully by checking against a given file list. If 'all' is 
    specified, `check_PreFreeSurfer.txt` file will be used, which has to be 
    present in the `<subjectsfolder>/subjects/specs` directory. If another 
    strings is given, the command will first check for a presence of a file with 
    such name in the spec folder (see before), and then check if it is a 
    valid path to a file. If a file is found, each line in a file should 
    represent a file or folder that has to be present in the 
    `<session id>/hcp/<session id>` directory. Folders should be separated by
    lines. Where a session id should be used, `{sessionid}` should be placed. It
    will be replaced with an actual session id at the time of checking. 

    A line that starts with a '#' is considered a comment and will be ignored. 
    If two alternatives are possible and either one of them satisfies the check,
    they should be placed on the same line, separated by a '|' character.

    Example content:
    
    ```
    T1w
    T1w T1w_acpc_dc.nii.gz
    T1w T2w_acpc_dc.nii.gz
    T1w T1w_acpc_brain_mask.nii.gz | T1w T1w_acpc_mask.nii.gz
    ```

    If full file checking is used:

    1/ the success of the run will be judged by the presence of all the files 
       as they are specified in the check file.
    2/ logs will be named:
       done        - the final file is present as well as all the required files
       incomplete  - the final file is present but not all the required files
       error       - the final file is missing
    3/ missing files will be printed to the stdout and a full report will be 
       appended to the log file.


    EXAMPLE USE
    ===========
    
    ```
    qunex hcp_PostFS sessions=fcMRI/subjects.hcp.txt subjectsfolder=subjects \\
          overwrite=no cores=10
    ```

    ```
    qunex hcp3 sessions=fcMRI/subjects.hcp.txt subjectsfolder=subjects \\
          overwrite=no cores=10 hcp_t2=NONE
    ```

    ----------------
    Written by Grega Repovš

    Changelog
    2017-01-08 Grega Repovš
             - Updated documentation.
    2018-04-23 Grega Repovš
             - Added new options and updated documentation.
    2018-12-13 Grega Repovš
             - Updated test files and documentation
    2019-01-12 Grega Repovš
             - Cleaned up, added updates by Lisa Ji
    2019-04-25 Grega Repovš
             - Changed subjects to sessions
    2019-05-26 Grega Repovš
             - Updated and simplified
             - Added full file checking
             - Made congruent with latest HCP pipeline
    2019-06-06 Grega Repovš
             - Enabled multiple log file locations
    2019-10-20 Grega Repovš
             - Adjusted parameters, help and processing to use integrated HCPpipelines
    2020-01-05 Grega Repovš
             - Updated documentation
    '''

    r = "\n---------------------------------------------------------"
    r += "\nSession id: %s \n[started on %s]" % (sinfo['id'], datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))
    r += "\n%s HCP PostFreeSurfer Pipeline [%s] ...\n" % (action("Running", options['run']), options['hcp_processing_mode'])

    run    = True
    report = "Error"

    try:
        doOptionsCheck(options, sinfo, 'hcp_PostFS')
        doHCPOptionsCheck(options, sinfo, 'hcp_PostFS')
        hcp = getHCPPaths(sinfo, options)

        # --- run checks

        if 'hcp' not in sinfo:
            r += "\n---> ERROR: There is no hcp info for session %s in batch.txt" % (sinfo['id'])
            run = False

        # -> FS results

        if os.path.exists(os.path.join(hcp['FS_folder'], 'mri', 'aparc+aseg.mgz')):
            r += "\n---> FS results present."
        else:
            r += "\n---> ERROR: Could not find Freesurfer processing results."
            run = False

        # -> T2w image

        if hcp['T2w'] in ['', 'NONE'] and options['hcp_processing_mode'] == 'HCPStyleData':
            r += "\n---> ERROR: The requested HCP processing mode is 'HCPStyleData', however, no T2w image was specified!"
            run = False

        ## -> longitudinal processing is currently not supported
        #
        # identify template if longitudinal run
        #
        # lttemplate     = ""
        # fslongitudinal = ""
        #
        # if options['hcp_fs_longitudinal']:
        #     if 'subject' not in sinfo:
        #         r += "\n     ... 'subject' field not defined in batch file, can not run longitudinal FS"
        #         run = False
        #     elif sinfo['subject'] == sinfo['id']:
        #         r += "\n     ... 'subject' field is equal to session 'id' field, can not run longitudinal FS"
        #         run = False
        #     else:
        #         lttemplate = hcp['FS_long_subject_template']
        #         lresults = os.path.join(hcp['FS_long_results'], 'label', 'rh.entorhinal_exvivo.label')
        #         if not os.path.exists(lresults):
        #             r += "\n     ... ERROR: Results of the longitudinal run not present [%s]" % (lresults)
        #             r += "\n                Please check your data and settings!" % (lresults)
        #             run = False   
        #         else:
        #             r += "\n     ... longitudinal template present"
        #             fslongitudinal = "run"


        comm = os.path.join(hcp['hcp_base'], 'PostFreeSurfer', 'PostFreeSurferPipeline.sh') + " "
        elements = [("path", sinfo['hcp']), 
                    ('subject', sinfo['id'] + options['hcp_suffix']),
                    ('surfatlasdir', os.path.join(hcp['hcp_Templates'], 'standard_mesh_atlases')),
                    ('grayordinatesdir', os.path.join(hcp['hcp_Templates'], '91282_Greyordinates')),
                    ('grayordinatesres', options['hcp_grayordinatesres']),
                    ('hiresmesh', options['hcp_hiresmesh']),
                    ('lowresmesh', options['hcp_lowresmesh']),
                    ('subcortgraylabels', os.path.join(hcp['hcp_Config'], 'FreeSurferSubcorticalLabelTableLut.txt')),
                    ('freesurferlabels', os.path.join(hcp['hcp_Config'], 'FreeSurferAllLut.txt')),
                    ('refmyelinmaps', os.path.join(hcp['hcp_Templates'], 'standard_mesh_atlases', 'Conte69.MyelinMap_BC.164k_fs_LR.dscalar.nii')),
                    ('mcsigma', options['hcp_mcsigma']),
                    ('regname', options['hcp_regname']),
                    ('inflatescale', options['hcp_inflatescale']),
                    ('processing-mode', options['hcp_processing_mode'])]

        comm += " ".join(['--%s="%s"' % (k, v) for k, v in elements if v])


        # -- Test files

        if False: #  fslongitudinal not supported:
            tfolder = hcp['hcp_long_nonlin']
            tfile = os.path.join(tfolder, sinfo['id'] + '.long.' + options['hcp_fs_longitudinal'] + '.corrThickness.164k_fs_LR.dscalar.nii')
        else:
            tfolder = hcp['hcp_nonlin']
            tfile = os.path.join(tfolder, sinfo['id'] + '.corrThickness.164k_fs_LR.dscalar.nii')

        if hcp['hcp_postfs_check']:
            fullTest = {'tfolder': hcp['base'], 'tfile': hcp['hcp_postfs_check'], 'fields': [('sessionid', sinfo['id'])], 'specfolder': options['specfolder']}
        else:
            fullTest = None

        # -- run

        if run:
            if options['run'] == "run":
                if overwrite and os.path.exists(tfile):
                    os.remove(tfile)

                r, endlog, report, failed = runExternalForFile(tfile, comm, 'Running HCP PostFS', overwrite=overwrite, thread=sinfo['id'], remove=options['log'] == 'remove', task=options['command_ran'], logfolder=options['comlogs'], logtags=options['logtag'], fullTest=fullTest, shell=True, r=r)

            # -- just checking
            else:
                passed, report, r, failed = checkRun(tfile, fullTest, 'HCP PostFS', r)
                if passed is None:
                    r += "\n---> HCP PostFS can be run"
                    report = "HCP PostFS can be run"
                    failed = 0
                r += "\n-----------------------------------------------------\nCommand to run:\n %s\n-----------------------------------------------------\n" % (comm.replace("--", "\n    --"))
        else:
            r += "\n---> Session can not be processed."
            report = "HCP PostFS can not be run"
            failed = 1

    except ge.CommandFailed as e:
        r +=  "\n\nERROR in completing %s at %s:\n     %s\n" % ('PostFreeSurfer', e.function, "\n     ".join(e.report))
        report = "PostFS failed"
        failed = 1
    except (ExternalFailed, NoSourceFolder), errormessage:
        r = str(errormessage)
        failed = 1
    except:
        r += "\nERROR: Unknown error occured: \n...................................\n%s...................................\n" % (traceback.format_exc())
        failed = 1

    r += "\n\nHCP PostFS %s on %s\n---------------------------------------------------------" % (action("completed", options['run']), datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))

    # print r
    return (r, (sinfo['id'], report, failed))


def hcpDiffusion(sinfo, options, overwrite=False, thread=0):
    """
    hcp_Diffusion [... processing options]
    hcpd [... processing options]

    USE
    ===

    Runs the Diffusion step of HCP Pipeline. It preprocesses diffusion weighted
    images (DWI). Specifically, after b0 intensity normalization, the b0 images
    of both phase encoding directions are used to calculate the susceptibility-induced
    B0 field deviations.The full timeseries from both phase encoding directions is
    used in the “eddy” tool for modeling of eddy current distortions and subject motion.
    Gradient distortion is corrected and the b0 image is registered to the T1w image
    using BBR. The diffusion data output from eddy are then resampled into 1.25mm
    native structural space and masked.Diffusion directions and the gradient deviation
    estimates are also appropriately rotated and registered into structural space.
    The function enables the use of a number of parameters to customize the specific
    preprocessing steps. A short name 'hcpd' can be used for this command.

    REQUIREMENTS
    ============

    The code expects the first HCP preprocessing step (hcp_PreFS) to have been run
    and finished successfully. It expects the DWI data to have been acquired in
    phase encoding reversed pairs, which should be present in the Diffusion folder
    in the sessions's root hcp folder.

    RESULTS
    =======

    The results of this step will be present in the Diffusion folder in the
    sessions's root hcp folder.

    RELEVANT PARAMETERS
    ===================

    general parameters
    ------------------

    When running the command, the following *general* processing parameters are
    taken into account:

    --sessions        ... The batch.txt file with all the sessions information
                          [batch.txt].
    --subjectsfolder  ... The path to the study/subjects folder, where the
                          imaging data is supposed to go [.].
    --cores           ... How many cores to utilize [1].
    --overwrite       ... Whether to overwrite existing data (yes) or not (no)
                          [no].
    --logfolder       ... The path to the folder where runlogs and comlogs
                          are to be stored, if other than default []
    --log             ... Whether to keep ('keep') or remove ('remove') the
                          temporary logs once jobs are completed ['keep'].
                          When a comma separated list is given, the log will
                          be created at the first provided location and then 
                          linked or copied to other locations. The valid 
                          locations are: 
                          * 'study'   for the default: 
                                      `<study>/processing/logs/comlogs`
                                      location,
                          * 'session' for `<sessionid>/logs/comlogs
                          * 'hcp'     for `<hcp_folder>/logs/comlogs
                          * '<path>'  for an arbitrary directory

    In addition a number of *specific* parameters can be used to guide the
    processing in this step:

    image acquisition details
    -------------------------

    --hcp_dwi_echospacing    ... Echo Spacing or Dwelltime of DWI images.
                                 [0.00035]

    distortion correction details
    -----------------------------

    --hcp_dwi_PEdir          ... The direction of unwarping. Use 1 for LR/RL
                                 Use 2 for AP/PA. Default is [2]
    --hcp_dwi_gdcoeffs       ... A path to a file containing gradient distortion
                                 coefficients, alternatively a string describing
                                 multiple options (see below), or "NONE", if not 
                                 used [NONE].

    Eddy post processing parameters
    -------------------------------

    --hcp_dwi_dof           ... Degrees of Freedom for post eddy registration to 
                                structural images. [6]
    --hcp_dwi_b0maxbval     ... Volumes with a bvalue smaller than this value 
                                will be considered as b0s. [50]
    --hcp_dwi_combinedata   ... Specified value is passed as the CombineDataFlag 
                                value for the eddy_postproc.sh script. If JAC 
                                resampling has been used in eddy, this value 
                                determines what to do with the output file.
                                2 - include in the output all volumes uncombined
                                    (i.e. output file of eddy)
                                1 - include in the output and combine only 
                                    volumes where both LR/RL (or AP/PA) pairs 
                                    have been acquired
                                0 - As 1, but also include uncombined single 
                                    volumes
                                [1]
    --hcp_dwi_extraeddyarg  ... A string specifying additional arguments to pass
                                to the DiffPreprocPipeline_Eddy.sh script and 
                                subsequently to the run_eddy.sh script and 
                                finally to the command that actually invokes the 
                                eddy binary. The string is to be writen as a 
                                contiguous set of tokens to be added. It will be
                                split by whitespace to be passed to the HCP 
                                DiffPreprocPipeline as a set of --extra-eddy-arg
                                arguments. ['']

    Additional parameters
    ---------------------

    --hcp_dwi_check         ... Whether to check the results of the Diffusion 
                                pipeline by presence of last file generated 
                                ('last'), the default list of all files ('all') 
                                or using a specific check file ('<path to file>')
                                ['last']


    Gradient Coefficient File Specification:
    ----------------------------------------

    `--hcp_dwi_gdcoeffs` parameter can be set to either 'NONE', a path to a specific
    file to use, or a string that describes, which file to use in which case. 
    Each option of the string has to be dividied by a pipe '|' character and it
    has to specify, which information to look up, a possible value, and a file 
    to use in that case, separated by a colon ':' character. The information 
    too look up needs to be present in the description of that session. 
    Standard options are e.g.:

    institution: Yale
    device: Siemens|Prisma|123456

    Where device is formated as <manufacturer>|<model>|<serial number>.

    If specifying a string it also has to include a `default` option, which 
    will be used in the information was not found. An example could be:

    "default:/data/gc1.conf|model:Prisma:/data/gc/Prisma.conf|model:Trio:/data/gc/Trio.conf"

    With the information present above, the file `/data/gc/Prisma.conf` would
    be used.
    
    Full file checking
    ------------------

    If `--hcp_prefs_check` parameter is set to `all` or a specific file, after
    the completion of processing, the command will check whether processing was
    completed successfully by checking against a given file list. If 'all' is 
    specified, `check_PreFreeSurfer.txt` file will be used, which has to be 
    present in the `<subjectsfolder>/subjects/specs` directory. If another 
    strings is given, the command will first check for a presence of a file with 
    such name in the spec folder (see before), and then check if it is a 
    valid path to a file. If a file is found, each line in a file should 
    represent a file or folder that has to be present in the 
    `<session id>/hcp/<session id>` directory. Folders should be separated by
    lines. Where a session id should be used, `{sessionid}` should be placed. It
    will be replaced with an actual session id at the time of checking. 

    A line that starts with a '#' is considered a comment and will be ignored. 
    If two alternatives are possible and either one of them satisfies the check,
    they should be placed on the same line, separated by a '|' character.

    Example content:
    
    ```
    T1w
    T1w T1w_acpc_dc.nii.gz
    T1w T2w_acpc_dc.nii.gz
    T1w T1w_acpc_brain_mask.nii.gz | T1w T1w_acpc_mask.nii.gz
    ```

    If full file checking is used:

    1/ the success of the run will be judged by the presence of all the files 
       as they are specified in the check file.
    2/ logs will be named:
       done        - the final file is present as well as all the required files
       incomplete  - the final file is present but not all the required files
       error       - the final file is missing
    3/ missing files will be printed to the stdout and a full report will be 
       appended to the log file.

    EXAMPLE USE
    ===========

    Example run from the base study folder with test flag
    --------------------------------------
    
    ```
    qunex hcp_Diffusion \
      --sessions="processing/batch.hcp.txt" \\
      --subjectsfolder="subjects" \\
      --cores="10" \\
      --overwrite="no" \\
      --test
    ```

    run using absolute paths with scheduler
    ---------------------------------------

    ```
    qunex hcpd \
      --sessions="<path_to_study_folder>/processing/batch.hcp.txt" \\
      --subjectsfolder="<path_to_study_folder>/subjects" \\
      --cores="4" \\
      --overwrite="yes" \\
      --scheduler="SLURM,time=24:00:00,ntasks=10,cpus-per-task=2,mem-per-cpu=2500,partition=YourPartition"
    ```

    ----------------
    Written by Grega Repovš

    Changelog
    2018-01-14 Alan Anticevic wrote inline documentation
    2019-04-25 Grega Repovs
             - Changed subjects to sessions
    2019-05-25 Grega Repovs
             - Updated with additional HCP parameters
             - Simplified calling and testing
             - Added gdcoeffs processing
             - Added full file checking
    2019-06-06 Grega Repovš
             - Enabled multiple log file locations
    2020-01-05 Grega Repovš
             - Updated documentation
    """

    r = "\n---------------------------------------------------------"
    r += "\nSession id: %s \n[started on %s]" % (sinfo['id'], datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))
    r += "\n%s HCP DiffusionPreprocessing Pipeline [%s] ..." % (action("Running", options['run']), options['hcp_processing_mode'])

    run    = True
    report = "Error"

    try:
        doOptionsCheck(options, sinfo, 'hcp_Diffusion')
        doHCPOptionsCheck(options, sinfo, 'hcp_Diffusion')
        hcp = getHCPPaths(sinfo, options)

        if 'hcp' not in sinfo:
            r += "---> ERROR: There is no hcp info for session %s in batch.txt" % (sinfo['id'])
            run = False

        # --- set up data

        if options['hcp_dwi_PEdir'] == "1":
            direction = [('pos', 'RL'), ('neg', 'LR')]
        else:
            direction = [('pos', 'AP'), ('neg', 'PA')]

        dwiData = dict()
        for ddir, dext in direction:
            dwiData[ddir] = "@".join(glob.glob(os.path.join(hcp['DWI_source'], "*_%s.nii.gz" % (dext))))

        for ddir in ['pos', 'neg']:
            dfiles = dwiData[ddir].split("@")
            if dfiles:
                r += "\n---> The following %s direction files were found:" % (ddir)
                for dfile in dfiles:
                    r += "\n     %s" % (os.path.basename(dfile))
            else:
                r += "\n---> ERROR: No %s direction files were found!"
                run = False

        # --- lookup gdcoeffs file if needed

        gdcfile, r, run = checkGDCoeffFile(options['hcp_dwi_gdcoeffs'], hcp=hcp, sinfo=sinfo, r=r, run=run)

        # -- set echospacing

        dwiinfo = [v for (k, v) in sinfo.iteritems() if k.isdigit() and v['name'] == 'DWI'][0]

        if 'EchoSpacing' in dwiinfo:
            echospacing = dwiinfo['EchoSpacing']
            r += "\n---> Using image specific EchoSpacing: %s ms" % (echospacing)                
        else:
            echospacing = options['hcp_dwi_echospacing']
            r += "\n---> Using study general EchoSpacing: %s ms" % (echospacing)


        # --- build the command

        comm = '%(script)s \
            --path="%(path)s" \
            --subject="%(subject)s" \
            --PEdir=%(PEdir)s \
            --posData="%(posData)s" \
            --negData="%(negData)s" \
            --echospacing="%(echospacing)s" \
            --gdcoeffs="%(gdcoeffs)s" \
            --dof="%(dof)s" \
            --b0maxbval="%(b0maxbval)s" \
            --combine-data-flag="%(combinedataflag)s" \
            --printcom="%(printcom)s"' % {
                'script'            : os.path.join(hcp['hcp_base'], 'DiffusionPreprocessing', 'DiffPreprocPipeline.sh'),
                'posData'           : dwiData['pos'],
                'negData'           : dwiData['neg'],
                'path'              : sinfo['hcp'],
                'subject'           : sinfo['id'] + options['hcp_suffix'],
                'echospacing'       : echospacing,
                'PEdir'             : options['hcp_dwi_PEdir'],
                'gdcoeffs'          : gdcfile,
                'dof'               : options['hcp_dwi_dof'],
                'b0maxbval'         : options['hcp_dwi_b0maxbval'],
                'combinedataflag'   : options['hcp_dwi_combinedata'],
                'printcom'          : options['hcp_printcom']}

        if options['hcp_dwi_extraeddyarg']:
            eddyoptions = options['hcp_dwi_extraeddyarg'].split()
            for eddyoption in eddyoptions:
                comm += " --extra-eddy-arg=" + eddyoption

        # -- Test files
        tfile = os.path.join(hcp['T1w_folder'], 'Diffusion', 'data.nii.gz')

        if hcp['hcp_dwi_check']:
            fullTest = {'tfolder': hcp['base'], 'tfile': hcp['hcp_dwi_check'], 'fields': [('sessionid', sinfo['id'])], 'specfolder': options['specfolder']}
        else:
            fullTest = None

        # -- Run

        if run:
            if options['run'] == "run":
                if overwrite and os.path.exists(tfile):
                    os.remove(tfile)

                r, endlog, report, failed  = runExternalForFile(tfile, comm, 'Running HCP Diffusion Preprocessing', overwrite=overwrite, thread=sinfo['id'], remove=options['log'] == 'remove', task=options['command_ran'], logfolder=options['comlogs'], logtags=options['logtag'], fullTest=fullTest, shell=True, r=r)

            # -- just checking
            else:
                passed, report, r, failed = checkRun(tfile, fullTest, 'HCP Diffusion', r)
                if passed is None:
                    r += "\n---> HCP Diffusion can be run"
                    report = "HCP Diffusion can be run"
                    failed = 0
                r += "\n-----------------------------------------------------\nCommand to run:\n %s\n-----------------------------------------------------\n" % (comm.replace("--", "\n    --"))
        else:
            r += "---> Session can not be processed."
            report = "HCP Diffusion can not be run"
            failed = 1

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = str(errormessage)
        failed = 1
    except:
        r += "\nERROR: Unknown error occured: \n...................................\n%s...................................\n" % (traceback.format_exc())
        failed = 1

    r += "\n\nHCP Diffusion Preprocessing %s on %s\n---------------------------------------------------------" % (action("completed", options['run']), datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))

    # print r
    return (r, (sinfo['id'], report, failed))



def hcpfMRIVolume(sinfo, options, overwrite=False, thread=0):
    '''
    hcp_fMRIVolume [... processing options]
    hcp4 [... processing options]

    USE
    ===

    Runs the fMRI Volume step of HCP Pipeline. It preprocesses BOLD images and
    linearly and nonlinearly registers them to the MNI atlas. It makes use of
    the PreFS and FS steps of the pipeline. It enables the use of a number of
    parameters to customize the specific preprocessing steps. A short name
    'hcp4' can be used for this command.

    REQUIREMENTS
    ============

    The code expects the first two HCP preprocessing steps (hcp_PreFS and
    hcp_FS) to have been run and finished successfully. It also tests for the
    presence of fieldmap or spin-echo images if they were specified. It does
    not make a thorough check for PreFS and FS steps due to the large number
    of files. If `hcp_fs_longitudinal` is specified, it also checks for 
    presence of the specifed longitudinal data.

    RESULTS
    =======

    The results of this step will be present in the MNINonLinear folder in the
    sessions's root hcp folder. In case a longitudinal FS template is used, the
    results will be stored in a `MNINonlinear_<FS longitudinal template name>`
    folder:

    study
    └─ subjects
       └─ subject1_session1
          └─ hcp
             └─ subject1_session1
               ├─ MNINonlinear
               │  └─ Results
               │     └─ BOLD_1
               └─ MNINonlinear_TemplateA
                  └─ Results
                     └─ BOLD_1

    RELEVANT PARAMETERS
    ===================

    general parameters
    ------------------

    When running the command, the following *general* processing parameters are
    taken into account:

    --sessions              ... The batch.txt file with all the sessions information
                                [batch.txt].
    --subjectsfolder        ... The path to the study/subjects folder, where the
                                imaging  data is supposed to go [.].
    --cores                 ... How many cores to utilize. This Parameter 
                                determines the parallelization on the subject
                                level [1].
    --threads               ... How many threads to utilize This Parameter
                                determines the parallelization on the bolds 
                                level [1].
    --bolds                 ... Which bold images (as they are specified in the
                                batch.txt file) to process. It can be a single
                                type (e.g. 'task'), a pipe separated list (e.g.
                                'WM|Control|rest') or 'all' to process all [all].
    --overwrite             ... Whether to overwrite existing data (yes) or not (no)
                                [no].
    --logfolder             ... The path to the folder where runlogs and comlogs
                                are to be stored, if other than default []
    --log                   ... Whether to keep ('keep') or remove ('remove') the
                                temporary logs once jobs are completed ['keep'].
                                When a comma separated list is given, the log will
                                be created at the first provided location and then 
                                linked or copied to other locations. The valid 
                                locations are: 
                                * 'study'   for the default: 
                                            `<study>/processing/logs/comlogs`
                                            location,
                                * 'session' for `<sessionid>/logs/comlogs
                                * 'hcp'     for `<hcp_folder>/logs/comlogs
                                * '<path>'  for an arbitrary directory
    --hcp_processing_mode   ... Controls whether the HCP acquisition and processing 
                                guidelines should be treated as requirements 
                                (HCPStyleData) or if additional processing 
                                functionality is allowed (LegacyStyleData). In this
                                case running processing with slice timing correction,
                                external BOLD reference, or without a distortion 
                                correction method.
    --hcp_folderstructure   ... Specifies the version of the folder structure to
                                use, 'initial' and 'hcpls' are supported ['hcpls']
    --hcp_filename          ... Specifies whether the standard ('standard') filenames
                                or the specified original names ('original') are to
                                be used ['standard']


    In addition a number of *specific* parameters can be used to guide the
    processing in this step:

    HCP Pipelines specific parameters
    ---------------------------------

    --hcp_bold_biascorrection   ... Whether to perform bias correction for BOLD 
                                    images. NONE or Legacy. [NONE]
    --hcp_bold_usejacobian      ... Whether to apply the jacobian of the 
                                    distortion correction to fMRI data.

    use of FS longitudinal template
    -------------------------------

    (-) --hcp_fs_longitudinal... The name of the FS longitudinal template if one
                                  was created and is to be used in this step.
    
    (-) This parameter is currently not supported

    processing validation
    ---------------------

    --hcp_bold_vol_check     ... Whether to check the results of the fMRIVolume 
                                 pipeline by presence of last file generated 
                                 ('last'), the default list of all files ('all') 
                                 or using a specific check file ('<path to file>')
                                 ['last']

    naming options
    --------------

    --hcp_suffix             ... Specifies a suffix to the session id if
                                 multiple variants of preprocessing are run,
                                 empty otherwise. []
    --hcp_bold_prefix        ... To be specified if multiple variants of BOLD
                                 preprocessing are run. The prefix is prepended
                                 to the bold name. [BOLD_]
    --hcp_filename           ... Specifies whether BOLD names are to be created
                                 using sequential numbers ('standard') using the 
                                 formula `<hcp_bold_prefix>_[N]` (e.g. BOLD_3) 
                                 or actual bold names ('original', e.g. 
                                 rfMRI_REST1_AP). ['standard']

    image acquisition details
    -------------------------

    --hcp_bold_echospacing      ... Echo Spacing or Dwelltime of BOLD images.
                                    [0.00035]
    --hcp_bold_sbref            ... Whether BOLD Reference images should be used
                                    - NONE or USE. [NONE]

    distortion correction details
    -----------------------------

    --hcp_bold_dcmethod      ... BOLD image deformation correction that should
                                 be used: TOPUP, FIELDMAP / SiemensFieldMap,
                                 GeneralElectricFieldMap or NONE. [TOPUP]
    --hcp_bold_echodiff      ... Delta TE for BOLD fieldmap images or NONE if
                                 not used. [NONE]
    --hcp_bold_sephasepos    ... Label for the positive image of the Spin Echo 
                                 Field Map pair [""]
    --hcp_bold_sephaseneg    ... Label for the negative image of the Spin Echo 
                                 Field Map pair [""]
    --hcp_bold_unwarpdir     ... The direction of unwarping. Can be specified
                                 separately for LR/RL : 'LR=x|RL=-x|x' or
                                 separately for PA/AP : 'PA=y|AP=y-|y-'. [y]
    --hcp_bold_res           ... Target image resolution. 2mm recommended. [2].
    --hcp_bold_gdcoeffs      ... Gradient distorsion correction coefficients
                                 or NONE. [NONE]

    slice timing correction (*)
    ---------------------------

    --hcp_bold_doslicetime      ... Whether to do slice timing correction TRUE or
                                    FALSE. []
    --hcp_bold_slicetimerparams ... A comma or pipe separated string of parameters 
                                    for FSL slicetimer.
    --hcp_bold_stcorrdir (!)    ... The direction of slice acquisition ('up' or
                                    'down'. [up]
    --hcp_bold_stcorrint (!)    ... Whether slices were acquired in an interleaved
                                    fashion (odd) or not (empty). [odd]

    (!) These parameters are deprecated. If specified, they will be added to 
    --hcp_bold_slicetimerparams.

    motion correction and atlas registration
    ----------------------------------------

    --hcp_bold_preregistertool ... What tool to use to preregister BOLDs before
                                   FSL BBR is run, epi_reg (default) or flirt.
                                   [epi_reg]
    --hcp_bold_movreg          ... Whether to use FLIRT (default and best for
                                   multiband images) or MCFLIRT for motion
                                   correction. [FLIRT]
    --hcp_bold_movref (*)      ... What reference to use for movement correction
                                   (independent, first). [independent]
    --hcp_bold_seimg (*)       ... What image to use for spin-echo distorsion
                                   correction (independent, first). [independent]
    --hcp_bold_refreg (*)      ... Whether to use only linaer (default) or also
                                   nonlinear registration of motion corrected bold
                                   to reference. [linear]
    --hcp_bold_mask (*)        ... Specifies what mask to use for the final bold:
                                   - T1_fMRI_FOV: combined T1w brain mask and fMRI 
                                     FOV masks (the default and HCPStyleData compliant), 
                                   - T1_DILATED_fMRI_FOV: a once dilated T1w brain 
                                     based mask combined with fMRI FOV
                                   - T1_DILATED2x_fMRI_FOV: a twice dilated T1w 
                                     brain based mask combined with fMRI FOV, 
                                   - fMRI_FOV: a fMRI FOV mask

    (*) These parameters are only valid when running HCPpipelines using the
    LegacyStyleData processing mode!

    These last parameters enable fine-tuning of preprocessing and deserve
    additional information. In general the defaults should be appropriate for
    multiband images, single-band can profit from specific adjustments.
      Whereas FLIRT is best used for motion registration of high-resolution BOLD
    images, lower resolution single-band images might be better motion aligned
    using MCFLIRT (--hcp_bold_movreg).
      As a movement correction target, either each BOLD can be independently
    registered to T1 image, or all BOLD images can be motion correction aligned
    to the first BOLD in the series and only that image is registered to the T1
    structural image (--hcp_bold_moveref). Do note that in this case also
    distortion correction will be computed for the first BOLD image in the
    series only and applied to all subsequent BOLD images after they were
    motion-correction aligned to the first BOLD.
      Similarly, for distortion correction, either the last preceeding spin-echo
    image pair can be used (independent) or only the first spin-echo pair is
    used for all BOLD images (first; --hcp_bold_seimg). Do note that this also
    affects the previous motion correction target setting. If independent
    spin-echo pairs are used, then the first BOLD image after a new spin-echo
    pair serves as a new starting motion-correction reference.
      If there is no spin-echo image pair and TOPUP correction was requested, an
    error will be reported and processing aborted. If there is no preceeding
    spin-echo pair, but there is at least one following the BOLD image in
    question, the first following spin-echo pair will be used and no error will
    be reported. The spin-echo pair used is reported in the log.
      When BOLD images are registered to the first BOLD in the series, due to
    larger movement between BOLD images it might be advantageous to use also
    nonlinear alignment to the first bold reference image (--hcp_bold_refreg).
      Lastly, for lower resolution BOLD images it might be better not to use
    subject specific T1 image based brain mask, but rather a mask generated on
    the BOLD image itself or based on the dilated standard MNI brain mask.
    
    Gradient Coefficient File Specification:
    ----------------------------------------

    `--hcp_bold_gdcoeffs` parameter can be set to either 'NONE', a path to a 
    specific file to use, or a string that describes, which file to use in which 
    case. Each option of the string has to be dividied by a pipe '|' character 
    and it has to specify, which information to look up, a possible value, and a 
    file to use in that case, separated by a colon ':' character. The information 
    too look up needs to be present in the description of that session. 
    Standard options are e.g.:

    institution: Yale
    device: Siemens|Prisma|123456

    Where device is formated as <manufacturer>|<model>|<serial number>.

    If specifying a string it also has to include a `default` option, which 
    will be used in the information was not found. An example could be:

    "default:/data/gc1.conf|model:Prisma:/data/gc/Prisma.conf|model:Trio:/data/gc/Trio.conf"

    With the information present above, the file `/data/gc/Prisma.conf` would
    be used.

    Full file checking
    ------------------

    If `--hcp_prefs_check` parameter is set to `all` or a specific file, after
    the completion of processing, the command will check whether processing was
    completed successfully by checking against a given file list. If 'all' is 
    specified, `check_PreFreeSurfer.txt` file will be used, which has to be 
    present in the `<subjectsfolder>/subjects/specs` directory. If another 
    strings is given, the command will first check for a presence of a file with 
    such name in the spec folder (see before), and then check if it is a 
    valid path to a file. If a file is found, each line in a file should 
    represent a file or folder that has to be present in the 
    `<session id>/hcp/<session id>` directory. Folders should be separated by
    lines. Where a session id should be used, `{sessionid}` should be placed. 
    Where the actual bold name should be used '{scan} should be placed. These
    will be replaced with the actual session id and bold names at the time of 
    checking. 

    A line that starts with a '#' is considered a comment and will be ignored. 
    If two alternatives are possible and either one of them satisfies the check,
    they should be placed on the same line, separated by a '|' character.

    Example content:
    
    ```
    {scan}
    {scan} {scan}_gdc_warp.nii.gz
    {scan} {scan}_gdc.nii.gz 
    {scan} {scan}_mc.nii.gz
    ```

    If full file checking is used:

    1/ the success of the run will be judged by the presence of all the files 
       as they are specified in the check file.
    2/ logs will be named:
       done        - the final file is present as well as all the required files
       incomplete  - the final file is present but not all the required files
       error       - the final file is missing
    3/ missing files will be printed to the stdout and a full report will be 
       appended to the log file.


    EXAMPLE USE
    ===========

    ```
    qunex hcp_fMRIVolume sessions=fcMRI/subjects.hcp.txt subjectsfolder=subjects \\
          overwrite=no cores=10
    ```

    ```
    qunex hcp4 sessions=fcMRI/subjects.hcp.txt subjectsfolder=subjects \\
          overwrite=no cores=10 hcp_bold_movref=first hcp_bold_seimg=first \\
          hcp_bold_refreg=nonlinear hcp_bold_mask=DILATED
    ```

    ----------------
    Written by Grega Repovš

    Changelog
    2017-02-06 Grega Repovš
             - Updated documentation.
    2017-09-02 Grega Repovs
             - Changed looking for relevant SE images
    2018-11-17 Jure Demsar
             - Parallel implementation.
    2018-11-20 Jure Demsar
             - Optimized parallelization that now covers all scenarios.
    2018-12-14 Grega Repovš
             - Added FS longitudinal option and documentation
    2019-01-12 Grega Repovš
             - Cleaned up, added updates by Lisa Ji
    2019-01-16 Grega Repovš
             - HCP Pipelines compatible.
    2019-04-25 Grega Repovš
             - Changed subjects to sessions
    2019-05-22 Grega Repovš
             - Added support for boldnamekey
             - Added reading of individual BOLD parameters
    2019-05-26 Grega Repovš
             - Updated, simplified calling and testing
             - Added full file checking
    2019-06-06 Grega Repovš
             - Enabled multiple log file locations
    2019-10-20 Grega Repovš
             - Initial adjustment of parameters, help and processing to use integrated HCPpipelines
    2020-01-05 Grega Repovš
             - Updated documentation
    2020-01-16 Grega Repovš
             - Introduced bold specific SE options and updated documentation
    2020-01-28 Grega Repovš
             - Made SE selection more rubust
    '''

    r = "\n---------------------------------------------------------"
    r += "\nSession id: %s \n[started on %s]" % (sinfo['id'], datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))
    r += "\n%s HCP fMRI Volume registration [%s] ... " % (action("Running", options['run']), options['hcp_processing_mode'])

    run    = True
    report = {'done': [], 'incomplete': [], 'failed': [], 'ready': [], 'not ready': [], 'skipped': []}

    try:
        # --- Base settings
        doOptionsCheck(options, sinfo, 'hcp_fMRIVolume')
        doHCPOptionsCheck(options, sinfo, 'hcp_fMRIVolume')
        hcp = getHCPPaths(sinfo, options)

        # --- bold filtering not yet supported!
        # btargets = options['bolds'].split("|")

        # --- run checks

        if 'hcp' not in sinfo:
            r += "\n---> ERROR: There is no hcp info for session %s in batch.txt" % (sinfo['id'])
            run = False

        # -> Pre FS results

        if os.path.exists(os.path.join(hcp['T1w_folder'], 'T1w_acpc_dc_restore_brain.nii.gz')):
            r += "\n---> PreFS results present."
        else:
            r += "\n---> ERROR: Could not find PreFS processing results."
            run = False

        # -> FS results

        if False:  # Longitudinal processing is currently unavailanle # options['hcp_fs_longitudinal']:
            tfolder = hcp['FS_long_results']
        else:
            tfolder = hcp['FS_folder']

        if os.path.exists(os.path.join(tfolder, 'mri', 'aparc+aseg.mgz')):
            r += "\n---> FS results present."
        else:
            r += "\n---> ERROR: Could not find Freesurfer processing results."
            # if options['hcp_fs_longitudinal']:
            #     r += "\n--->        Please check that you have run FS longitudinal as specified,"
            #     r += "\n--->        and that %s template was successfully generated." % (options['hcp_fs_longitudinal'])

            run = False

        # -> PostFS results

        if False:  # Longitudinal processing is currently unavailanle # options['hcp_fs_longitudinal']:
            tfile = os.path.join(hcp['hcp_long_nonlin'], 'fsaverage_LR32k', sinfo['id'] + '.long.' + options['hcp_fs_longitudinal'] + options['hcp_suffix'] + '.32k_fs_LR.wb.spec')
        else:
            tfile = os.path.join(hcp['hcp_nonlin'], 'fsaverage_LR32k', sinfo['id'] + options['hcp_suffix'] + '.32k_fs_LR.wb.spec')

        if os.path.exists(tfile):
            r += "\n---> PostFS results present."
        else:
            r += "\n---> ERROR: Could not find PostFS processing results."
            # if options['hcp_fs_longitudinal']:
            #     r += "\n--->        Please check that you have run PostFS on FS longitudinal as specified,"
            #     r += "\n--->        and that %s template was successfully used." % (options['hcp_fs_longitudinal'])
            run = False
        
        # --- lookup gdcoeffs file if needed

        gdcfile, r, run = checkGDCoeffFile(options['hcp_bold_gdcoeffs'], hcp=hcp, sinfo=sinfo, r=r, run=run)

        # -> Check for SE images

        sepresent = []
        sepairs = {}
        sesettings = False

        if options['hcp_bold_dcmethod'].lower() == 'topup':
                
            # -- spin echo settings

            sesettings = True
            for p in ['hcp_bold_sephaseneg', 'hcp_bold_sephasepos', 'hcp_bold_unwarpdir']:
                if not options[p]:
                    r += '\n---> ERROR: TOPUP requested but %s parameter is not set! Please review parameter file!' % (p)
                    boldok = False
                    sesettings = False
                    run = False

            if sesettings:
                r += "\n---> Looking for spin echo fieldmap set images [%s/%s]." % (options['hcp_bold_sephasepos'], options['hcp_bold_sephaseneg'])

                for bold in range(50):
                    spinok = False

                    # check if folder exists
                    sepath = glob.glob(os.path.join(hcp['source'], "SpinEchoFieldMap%d*" % (bold)))
                    if sepath:
                        sepath = sepath[0]
                        r += "\n     ... identified folder %s" % (os.path.basename(sepath))
                        # get all *.nii.gz files in that folder
                        images = glob.glob(os.path.join(sepath, "*.nii.gz"))

                        # variable for checking se status
                        spinok = True
                        spinPos, spinNeg = None, None
                        
                        # search in images
                        for i in images:
                            # look for phase positive 
                            if "_" + options['hcp_bold_sephasepos'] in os.path.basename(i):
                                spinPos = i
                                r, spinok = checkForFile2(r, spinPos, "\n     ... phase positive %s spin echo fieldmap image present" % (options['hcp_bold_sephasepos']), "\n         ERROR: %s spin echo fieldmap image missing!" % (options['hcp_bold_sephasepos']), status=spinok)
                            # look for phase negative
                            elif "_" + options['hcp_bold_sephaseneg'] in os.path.basename(i):
                                spinNeg = i
                                r, spinok = checkForFile2(r, spinNeg, "\n     ... phase negative %s spin echo fieldmap image present" % (options['hcp_bold_sephaseneg']), "\n         ERROR: %s spin echo fieldmap image missing!" % (options['hcp_bold_sephaseneg']), status=spinok)

                        if not all([spinPos, spinNeg]):
                            r += "\n---> ERROR: Either one of both pairs of SpinEcho images are missing in the %s folder! Please check your data or settings!" % (os.path.basename(sepath))
                            spinok = False

                    if spinok:
                        sepresent.append(bold)
                        sepairs[bold] = {'spinPos': spinPos, 'spinNeg': spinNeg}

                # --- Process unwarp direction

                unwarpdirs = [[f.strip() for f in e.strip().split("=")] for e in options['hcp_bold_unwarpdir'].split("|")]
                unwarpdirs = [['default', e[0]] if len(e) == 1 else e for e in unwarpdirs]
                unwarpdirs = dict(unwarpdirs)

        # --- Get sorted bold numbers

        bolds, bskip, report['boldskipped'], r = useOrSkipBOLD(sinfo, options, r)
        if report['boldskipped']:
            if options['hcp_filename'] == 'original':
                report['skipped'] = [bi.get('filename', str(bn)) for bn, bnm, bt, bi in bskip]
            else:
                report['skipped'] = [str(bn) for bn, bnm, bt, bi in bskip]

        # --- Preprocess

        spinP       = 0
        spinN       = 0
        spinNeg     = "NONE"  # AP or LR
        spinPos     = "NONE"  # PA or RL
        refimg      = "NONE"
        futureref   = "NONE"
        topupconfig = ""

        boldsData = []

        if bolds:
            firstSE = bolds[0][3].get('se', None)

        for bold, boldname, boldtask, boldinfo in bolds:

            if 'filename' in boldinfo and options['hcp_filename'] == 'original':
                printbold  = boldinfo['filename']
                boldsource = boldinfo['filename']
                boldtarget = boldinfo['filename']
            else:
                printbold  = str(bold)
                boldsource = 'BOLD_%d' % (bold)
                boldtarget = "%s%s" % (options['hcp_bold_prefix'], printbold)

            r += "\n\n---> %s BOLD %s" % (action("Preprocessing settings (unwarpdir, refimage, moveref, seimage) for", options['run']), printbold)
            boldok = True

            # --- set unwarpdir

            if "o" in boldinfo:
                orient    = "_" + boldinfo['o']
                unwarpdir = unwarpdirs.get(boldinfo['o'])
                if unwarpdir is None:
                    r += '\n     ... ERROR: No unwarpdir is defined for %s! Please check hcp_bold_unwarpdir parameter!' % (boldinfo['o'])
                    boldok = False
            elif 'phenc' in boldinfo:
                orient    = "_" + boldinfo['phenc']
                unwarpdir = unwarpdirs.get(boldinfo['phenc'])
                if unwarpdir is None:
                    r += '\n     ... ERROR: No unwarpdir is defined for %s! Please check hcp_bold_unwarpdir parameter!' % (boldinfo['phenc'])
                    boldok = False
            else:
                orient = ""
                unwarpdir = unwarpdirs.get('default')
                if unwarpdir is None:
                    r += '\n     ... ERROR: No default unwarpdir is set! Please check hcp_bold_unwarpdir parameter!'
                    boldok = False

            if orient:
                r += "\n     ... phase encoding direction: %s" % (orient[1:])
            else:
                r += "\n     ... phase encoding direction not specified"
                
            r += "\n     ... unwarp direction: %s" % (unwarpdir)

            # --- set reference
            #
            # Need to make sure the right reference is used in relation to LR/RL AP/PA bolds
            # - have to keep track of whether an old topup in the same direction exists
            #
            
            # --- check for bold image

            if 'filename' in boldinfo and options['hcp_filename'] == 'original':
                boldroot = boldinfo['filename']
            else:
                boldroot = boldsource + orient

            boldimg = os.path.join(hcp['source'], "%s%s" % (boldroot, options['fctail']), "%s_%s.nii.gz" % (sinfo['id'], boldroot))
            r, boldok = checkForFile2(r, boldimg, "\n     ... bold image present", "\n     ... ERROR: bold image missing [%s]!" % (boldimg), status=boldok)

            # --- check for ref image

            if options['hcp_bold_sbref'].lower() == 'use':
                refimg = os.path.join(hcp['source'], "%s_SBRef%s" % (boldroot, options['fctail']), "%s_%s_SBRef.nii.gz" % (sinfo['id'], boldroot))
                r, boldok = checkForFile2(r, refimg, '\n     ... reference image present', '\n     ... ERROR: bold reference image missing!', status=boldok)
            else:
                r += "\n     ... reference image not used"

            # --- check for spin-echo-fieldmap image

            echospacing = ""

            if options['hcp_bold_dcmethod'].lower() == 'topup' and sesettings:
                
                if not sepresent:
                    r += '\n     ... ERROR: No spin echo fieldmap set images present!'
                    boldok = False

                elif options['hcp_bold_seimg'] == 'first':
                    if firstSE is None:
                        spinN = sepresent[0]
                        r += "\n     ... using the first recorded spin echo fieldmap set %d" % (spinN)
                    else:
                        spinN = firstSE
                        r += "\n     ... using the spin echo fieldmap set for the first bold run, %d" % (spinN)
                    spinNeg = sepairs[spinN]['spinNeg']
                    spinPos = sepairs[spinN]['spinPos']

                else:
                    spinN = False
                    if 'se' in boldinfo:
                        spinN = int(boldinfo['se'])
                    else:
                        for sen in sepresent:
                            if sen <= bold:
                                spinN = sen
                            elif not spinN:
                                spinN = sen
                    spinNeg = sepairs[spinN]['spinNeg']
                    spinPos = sepairs[spinN]['spinPos']
                    r += "\n     ... using spin echo fieldmap set %d" % (spinN)
                    r += "\n         -> SE Positive image : %s" % (os.path.basename(spinPos))
                    r += "\n         -> SE Negative image : %s" % (os.path.basename(spinNeg))

                # -- are we using a new SE image?

                if spinN != spinP:
                    spinP = spinN
                    futureref = "NONE"

                # --> check for topupconfig

                if options['hcp_bold_topupconfig']:
                    topupconfig = options['hcp_bold_topupconfig']
                    if not os.path.exists(options['hcp_bold_topupconfig']):
                        topupconfig = os.path.join(hcp['hcp_Config'], options['hcp_bold_topupconfig'])
                        if not os.path.exists(topupconfig):
                            r += "\n---> ERROR: Could not find TOPUP configuration file: %s." % (options['hcp_bold_topupconfig'])
                            run = False
                        else:
                            r += "\n---> TOPUP configuration file present."
                    else:
                        r += "\n---> TOPUP configuration file present."

                # -- set echospacing

                if 'EchoSpacing' in boldinfo:
                    echospacing = boldinfo['EchoSpacing']
                    r += "\n     ... using image specific EchoSpacing: %s s" % (echospacing)                
                elif options['hcp_bold_echospacing']:
                    echospacing = options['hcp_bold_echospacing']
                    r += "\n     ... using study general EchoSpacing: %s s" % (echospacing)
                else:
                    echospacing = ""
                    r += "\n---> ERROR: EchoSpacing is not set! Please review parameter file."
                    boldok = False

            # --- check for Siemens double TE-fieldmap image

            elif options['hcp_bold_dcmethod'].lower() in ['fieldmap', 'siemensfieldmap']:
                fieldok = True
                r, fieldok = checkForFile2(r, hcp['fmapmag'], '\n     ... Siemens fieldmap magnitude image present ', '\n     ... ERROR: Siemens fieldmap magnitude image missing!', status=fieldok)
                r, fieldok = checkForFile2(r, hcp['fmapphase'], '\n     ... Siemens fieldmap phase image present ', '\n     ... ERROR: Siemens fieldmap phase image missing!', status=fieldok)
                if not is_number(options['hcp_bold_echospacing']):
                    fieldok = False
                    r += '\n     ... ERROR: hcp_bold_echospacing not defined correctly: "%s"!' % (options['hcp_bold_echospacing'])
                if not is_number(options['hcp_bold_echodiff']):
                    fieldok = False
                    r += '\n     ... ERROR: hcp_bold_echodiff not defined correctly: "%s"!' % (options['hcp_bold_echodiff'])
                boldok = boldok and fieldok

            # --- check for GE fieldmap image

            elif options['hcp_bold_dcmethod'].lower() in ['generalelectricfieldmap']:
                fieldok = True
                r, fieldok = checkForFile2(r, hcp['fmapge'], '\n     ... GeneralElectric fieldmap image present ', '\n     ... ERROR: GeneralElectric fieldmap image missing!', status=fieldok)
                boldok = boldok and fieldok

            # --- NO DC used

            elif options['hcp_bold_dcmethod'].lower() == 'none':
                r += '\n     ... No distortion correction used '
                if options['hcp_processing_mode'] == 'HCPStyleData':
                    r += "\n---> ERROR: The requested HCP processing mode is 'HCPStyleData', however, no distortion correction method was specified!\n            Consider using LegacyStyleData processing mode."
                    run = False

            # --- ERROR

            else:
                r += '\n     ... ERROR: Unknown distortion correction method: %s! Please check your settings!' % (options['hcp_bold_dcmethod'])
                boldok = False

            # ---> Check the mask used
            if options['hcp_bold_mask']:
                if options['hcp_bold_mask'] != 'T1_fMRI_FOV' and options['hcp_processing_mode'] == 'HCPStyleData':
                    r += "\n---> ERROR: The requested HCP processing mode is 'HCPStyleData', however, %s was specified as bold mask to use!\n            Consider either using 'T1_fMRI_FOV' for the bold mask or LegacyStyleData processing mode."
                    run = False
                else:
                    r += '\n     ... using %s as BOLD mask' % (options['hcp_bold_mask'])
            else:
                r += '\n     ... using the HCPpipelines default BOLD mask'

            # --- set movement reference image

            fmriref = futureref
            if options['hcp_bold_movref'] == 'first':
                if futureref == "NONE":
                    futureref = boldtarget

            # --- are we using previous reference

            if fmriref is not "NONE":
                r += '\n     ... using %s as movement correction reference' % (fmriref)
                refimg = 'NONE'
                if options['hcp_processing_mode'] == 'HCPStyleData' and options['hcp_bold_refreg'] == 'nonlinear':
                    r += "\n---> ERROR: The requested HCP processing mode is 'HCPStyleData', however, a nonlinear registration to an external BOLD was specified!\n            Consider using LegacyStyleData processing mode."
                    run = False

            # store required data
            b = {'boldsource':   boldsource,
                 'boldtarget':   boldtarget,
                 'printbold':    printbold,
                 'run':          run,
                 'boldok':       boldok,
                 'boldimg':      boldimg,
                 'refimg':       refimg,
                 'gdcfile':      gdcfile,
                 'unwarpdir':    unwarpdir,
                 'echospacing':  echospacing,
                 'spinNeg':      spinNeg,
                 'spinPos':      spinPos,
                 'topupconfig':  topupconfig,
                 'fmriref':      fmriref}
            boldsData.append(b)

        # --- Process
        r += "\n"

        threads = min(options['threads'], len(boldsData))
        r += "\n%s BOLD images on %d threads" % (action("Running", options['run']), threads)

        if (threads == 1): # serial execution
            # loop over bolds
            for b in boldsData:
                # process
                result = executeHCPfMRIVolume(sinfo, options, overwrite, hcp, b)

                # merge r
                r += result['r']

                # merge report
                tempReport            = result['report']
                report['done']       += tempReport['done']
                report['incomplete'] += tempReport['incomplete']
                report['failed']     += tempReport['failed']
                report['ready']      += tempReport['ready']
                report['not ready']  += tempReport['not ready']
                report['skipped']    += tempReport['skipped']

        else: # parallel execution
            # if moveref equals first and seimage equals independent (complex scenario)
            if (options['hcp_bold_movref'] == 'first') and (options['hcp_bold_seimg'] == 'independent'):
                # loop over bolds to prepare processing pools
                boldsPool = []
                for b in boldsData:
                    fmriref = b['fmriref']
                    if (fmriref == "NONE"): # if fmriref is "NONE" then process the previous pool followed by this one as single
                        r, report = executeMultipleHCPfMRIVolume(sinfo, options, overwrite, hcp, boldsPool, r, report)
                        boldsPool = []
                        r, report = executeSingleHCPfMRIVolume(sinfo, options, overwrite, hcp, b, r, report)
                    else: # else add to pool
                        boldsPool.append(b)

                # execute remaining pool
                r, report = executeMultipleHCPfMRIVolume(sinfo, options, overwrite, hcp, boldsPool, r, report)                      
            
            else:
                # if moveref equals first then process first one in serial
                if options['hcp_bold_movref'] == 'first':
                    # process first one
                    b = boldsData[0]
                    r, report = executeSingleHCPfMRIVolume(sinfo, options, overwrite, hcp, b, r, report)
                    
                    # remove first one from array then process others in parallel
                    boldsData.pop(0)

                # process the rest in parallel
                r, report = executeMultipleHCPfMRIVolume(sinfo, options, overwrite, hcp, boldsData, r, report)

        rep = []
        for k in ['done', 'incomplete', 'failed', 'ready', 'not ready', 'skipped']:
            if len(report[k]) > 0:
                rep.append("%s %s" % (", ".join(report[k]), k))
        
        report = (sinfo['id'], "HCP fMRI Volume: bolds " + "; ".join(rep), len(report['failed'] + report['incomplete'] + report['not ready']))

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = str(errormessage)
        report = (sinfo['id'], 'HCP fMRI Volume failed', 1)
    except:
        r += "\nERROR: Unknown error occured: \n...................................\n%s...................................\n" % (traceback.format_exc())
        report = (sinfo['id'], 'HCP fMRI Volume failed', 1)

    r += "\n\nHCP fMRIVolume %s on %s\n---------------------------------------------------------" % (action("completed", options['run']), datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))

    # rint r
    return (r, report)

def executeSingleHCPfMRIVolume(sinfo, options, overwrite, hcp, b, r, report):
    # process
    result = executeHCPfMRIVolume(sinfo, options, overwrite, hcp, b)

    # merge r
    r += result['r']

    # merge report
    tempReport            = result['report']
    report['done']       += tempReport['done']
    report['incomplete'] += tempReport['incomplete']
    report['failed']     += tempReport['failed']
    report['ready']      += tempReport['ready']
    report['not ready']  += tempReport['not ready']
    report['skipped']    += tempReport['skipped']

    return r, report

def executeMultipleHCPfMRIVolume(sinfo, options, overwrite, hcp, boldsData, r, report):
    # threads
    threads = min(options['threads'], len(boldsData))

    # create a multiprocessing Pool
    processPoolExecutor = ProcessPoolExecutor(threads)

    # partial function
    f = partial(executeHCPfMRIVolume, sinfo, options, overwrite, hcp)
    results = processPoolExecutor.map(f, boldsData)

    # merge r and report
    for result in results:
        r += result['r']
        tempReport            = result['report']
        report['done']       += tempReport['done']
        report['incomplete'] += tempReport['incomplete']
        report['failed']     += tempReport['failed']
        report['ready']      += tempReport['ready']
        report['not ready']  += tempReport['not ready']
        report['skipped']    += tempReport['skipped']

    return r, report

def executeHCPfMRIVolume(sinfo, options, overwrite, hcp, b):
    # extract data
    boldsource  = b['boldsource']
    boldtarget  = b['boldtarget']
    printbold   = b['printbold']
    gdcfile     = b['gdcfile']
    run         = b['run']
    boldok      = b['boldok']
    boldimg     = b['boldimg']
    refimg      = b['refimg']
    unwarpdir   = b['unwarpdir']
    echospacing = b['echospacing']
    spinNeg     = b['spinNeg']
    spinPos     = b['spinPos']
    topupconfig = b['topupconfig']
    fmriref     = b['fmriref']

    # prepare return variables
    r = ""
    report = {'done': [], 'incomplete': [], 'failed': [], 'ready': [], 'not ready': [], 'skipped': []}

    try:

        # --- process additional parameters

        slicetimerparams = ""

        if options['hcp_bold_doslicetime'].lower() == 'true':

            slicetimerparams = re.split(' +|,|\|', options['hcp_bold_slicetimerparams'])

            stappendItems = []
            if options['hcp_bold_stcorrdir'] == 'down':
                stappendItems.append('--down')
            if options['hcp_bold_stcorrint'] == 'odd':
                stappendItems.append('--odd')
            
            for stappend in stappendItems:
                if stappend not in slicetimerparams:
                    slicetimerparams.append(stappend)

            slicetimerparams = [e for e in slicetimerparams if e]
            slicetimerparams = "@".join(slicetimerparams)

        # --- Set up the command

        if fmriref == 'NONE':
            fmrirefparam = ""
        else:
            fmrirefparam = fmriref

        comm = os.path.join(hcp['hcp_base'], 'fMRIVolume', 'GenericfMRIVolumeProcessingPipeline.sh') + " "

        elements = [("path",                sinfo['hcp']),
                    ("subject",             sinfo['id'] + options['hcp_suffix']),
                    ("fmriname",            boldtarget),
                    ("fmritcs",             boldimg),
                    ("fmriscout",           refimg),
                    ("SEPhaseNeg",          spinNeg),
                    ("SEPhasePos",          spinPos),
                    ("fmapmag",             hcp['fmapmag']),
                    ("fmapphase",           hcp['fmapphase']),
                    ("fmapgeneralelectric", hcp['fmapge']),
                    ("echospacing",         echospacing),
                    ("echodiff",            options['hcp_bold_echodiff']),
                    ("unwarpdir",           unwarpdir),
                    ("fmrires",             options['hcp_bold_res']),
                    ("dcmethod",            options['hcp_bold_dcmethod']),
                    ("biascorrection",      options['hcp_bold_biascorrection']),
                    ("gdcoeffs",            gdcfile),
                    ("topupconfig",         topupconfig),
                    ("dof",                 options['hcp_bold_dof']),
                    ("printcom",            options['hcp_printcom']),
                    ("usejacobian",         options['hcp_bold_usejacobian']),
                    ("mctype",              options['hcp_bold_movreg'].upper()),
                    ("preregistertool",     options['hcp_bold_preregistertool']),
                    ("processing-mode",     options['hcp_processing_mode']),
                    ("doslicetime",         options['hcp_bold_doslicetime'].upper()),
                    ("slicetimerparams",    slicetimerparams),
                    ("fmriref",             fmrirefparam),
                    ("fmrirefreg",          options['hcp_bold_refreg']),
                    ("boldmask",            options['hcp_bold_mask'])]

        comm += " ".join(['--%s="%s"' % (k, v) for k, v in elements if v])

        # -- Test files

        if False:   # Longitudinal option currently not supported options['hcp_fs_longitudinal']:
            tfile = os.path.join(hcp['hcp_long_nonlin'], 'Results', "%s_%s" % (boldtarget, options['hcp_fs_longitudinal']), "%s%d_%s.nii.gz" % (options['hcp_bold_prefix'], bold, options['hcp_fs_longitudinal']))
        else:
            tfile = os.path.join(hcp['hcp_nonlin'], 'Results', boldtarget, "%s.nii.gz" % (boldtarget))

        if hcp['hcp_bold_vol_check']:
            fullTest = {'tfolder': hcp['base'], 'tfile': hcp['hcp_bold_vol_check'], 'fields': [('sessionid', sinfo['id']), ('scan', boldtarget)], 'specfolder': options['specfolder']}
        else:
            fullTest = None

        # -- Run

        if run and boldok:            
            if options['run'] == "run":
                if overwrite or not os.path.exists(tfile):

                    # ---> Clean up existing data
                    # -> bold working folder
                    bold_folder = os.path.join(hcp['base'], boldtarget)
                    if os.path.exists(bold_folder):
                        r += "\n     ... removing preexisting working bold folder [%s]" % (bold_folder)
                        shutil.rmtree(bold_folder)

                    # -> bold MNINonLinear results folder
                    bold_folder = os.path.join(hcp['hcp_nonlin'], 'Results', boldtarget)
                    if os.path.exists(bold_folder):
                        r += "\n     ... removing preexisting MNINonLinar results bold folder [%s]" % (bold_folder)
                        shutil.rmtree(bold_folder)

                    # -> bold T1w results folder
                    bold_folder = os.path.join(hcp['T1w_folder'], 'Results', boldtarget)
                    if os.path.exists(bold_folder):
                        r += "\n     ... removing preexisting T1w results bold folder [%s]" % (bold_folder)
                        shutil.rmtree(bold_folder)

                    # -> xfms in T1w folder
                    xfms_file = os.path.join(hcp['T1w_folder'], 'xfms', "%s2str.nii.gz" % (boldtarget))
                    if os.path.exists(xfms_file):
                        r += "\n     ... removing preexisting xfms file [%s]" % (xfms_file)
                        os.remove(xfms_file)

                    # -> xfms in MNINonLinear folder
                    xfms_file = os.path.join(hcp['hcp_nonlin'], 'xfms', "%s2str.nii.gz" % (boldtarget))
                    if os.path.exists(xfms_file):
                        r += "\n     ... removing preexisting xfms file [%s]" % (xfms_file)
                        os.remove(xfms_file)

                    # -> xfms in MNINonLinear folder
                    xfms_file = os.path.join(hcp['hcp_nonlin'], 'xfms', "standard2%s.nii.gz" % (boldtarget))
                    if os.path.exists(xfms_file):
                        r += "\n     ... removing preexisting xfms file [%s]" % (xfms_file)
                        os.remove(xfms_file)

                r, endlog, _, failed = runExternalForFile(tfile, comm, 'Running HCP fMRIVolume', overwrite=overwrite, thread=sinfo['id'], remove=options['log'] == 'remove', task=options['command_ran'], logfolder=options['comlogs'], logtags=[options['logtag'], boldtarget], fullTest=fullTest, shell=True, r=r)

                if failed:
                    report['failed'].append(printbold)                    
                else:
                    report['done'].append(printbold)
            
            # -- just checking
            else:
                passed, _, r, failed = checkRun(tfile, fullTest, 'HCP fMRIVolume ' + boldtarget, r)
                if passed is None:
                    r += "\n     ... HCP fMRIVolume can be run"
                    r += "\n-----------------------------------------------------\nCommand to run:\n %s\n-----------------------------------------------------\n" % (comm.replace("--", "\n    --"))
                    report['ready'].append(printbold)
                else:
                    report['skipped'].append(printbold)

        elif run:
            report['not ready'].append(printbold)
            if options['run'] == "run":
                r += "\n     ... ERROR: images or data parameters missing, skipping this BOLD!"
            else:
                r += "\n     ... ERROR: images or data parameters missing, this BOLD would be skipped!"
        else:
            report['not ready'].append(printbold)
            if options['run'] == "run":
                r += "\n     ... ERROR: No hcp info for subject, skipping this BOLD!"
            else:
                r += "\n     ... ERROR: No hcp info for subject, this BOLD would be skipped!"

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = "\n\n\n --- Failed during processing of bold %s with error:\n" % (printbold)
        r += str(errormessage)
        report['failed'].append(printbold)
    except:
        r += "\n --- Failed during processing of bold %s with error:\n %s\n" % (printbold, traceback.format_exc())
        report['failed'].append(printbold)

    # r += "\n     ... DONE!"

    return {'r': r, 'report': report}


def hcpfMRISurface(sinfo, options, overwrite=False, thread=0):
    '''
    hcp_fMRISurface [... processing options]
    hcp5 [... processing options]

    USE
    ===

    Runs the fMRI Surface step of HCP Pipeline. It uses the FreeSurfer
    segmentation and surface reconstruction to map BOLD timeseries to
    grayordinate representation and generates .dtseries.nii files.
    A short name 'hcp5' can be used for this command.

    REQUIREMENTS
    ============

    The code expects all the previous HCP preprocessing steps (hcp_PreFS,
    hcp_FS, hcp_PostFS, hcp_fMRIVolume) to have been run and finished
    successfully. The command will test for presence of key files but do note
    that it won't run a thorough check for all the required files.

    RESULTS
    =======

    The results of this step will be present in the MNINonLinear folder in the
    sessions's root hcp folder. In case a longitudinal FS template is used, the
    results will be stored in a `MNINonlinear_<FS longitudinal template name>`
    folder:

    study
    └─ subjects
       └─ subject1_session1
          └─ hcp
             └─ subject1_session1
               ├─ MNINonlinear
               │  └─ Results
               │     └─ BOLD_1
               └─ MNINonlinear_TemplateA
                  └─ Results
                     └─ BOLD_1

    RELEVANT PARAMETERS
    ===================

    general parameters
    ------------------

    When running the command, the following *general* processing parameters are
    taken into account:

    --sessions        ... The batch.txt file with all the sessions information
                          [batch.txt].
    --subjectsfolder  ... The path to the study/subjects folder, where the
                          imaging data is supposed to go [.].
    --cores           ... How many cores to utilize. This Parameter determines
                          the parallelization on the subject level [1].
    --threads         ... How many threads to utilize This Parameter determines 
                          the parallelization on the bolds level [1].
    --bolds           ... Which bold images (as they are specified in the
                          batch.txt file) to process. It can be a single
                          type (e.g. 'task'), a pipe separated list (e.g.
                          'WM|Control|rest') or 'all' to process all [all].
    --overwrite       ... Whether to overwrite existing data (yes) or not (no)
                          [no].
    --logfolder       ... The path to the folder where runlogs and comlogs
                          are to be stored, if other than default []
    --log             ... Whether to keep ('keep') or remove ('remove') the
                          temporary logs once jobs are completed ['keep'].
                          When a comma separated list is given, the log will
                          be created at the first provided location and then 
                          linked or copied to other locations. The valid 
                          locations are: 
                          * 'study'   for the default: 
                                      `<study>/processing/logs/comlogs`
                                      location,
                          * 'session' for `<sessionid>/logs/comlogs
                          * 'hcp'     for `<hcp_folder>/logs/comlogs
                          * '<path>'  for an arbitrary directory

    --hcp_folderstructure   ... Specifies the version of the folder structure to
                                use, 'initial' and 'hcpls' are supported ['hcpls']
    --hcp_filename          ... Specifies whether the standard ('standard') filenames
                                or the specified original names ('original') are to
                                be used ['standard']

    In addition a number of *specific* parameters can be used to guide the
    processing in this step:

    processing validation
    ---------------------

    --hcp_bold_surf_check    ... Whether to check the results of the fMRISurface 
                                 pipeline by presence of last file generated 
                                 ('last'), the default list of all files ('all') 
                                 or using a specific check file ('<path to file>')
                                 ['last']

    use of FS longitudinal template
    -------------------------------

    * --hcp_fs_longitudinal  ... The name of the FS longitudinal template if one
                                 was created and is to be used in this step.
    
    * this parameter is curently not in use

    naming options
    --------------

    --hcp_suffix             ... Specifies a suffix to the session id if
                                 multiple variants of preprocessing are run,
                                 empty otherwise. []
    --hcp_bold_prefix        ... To be specified if multiple variants of BOLD
                                 preprocessing are run. The prefix is prepended
                                 to the bold name. []

    grayordinate image mapping details
    ----------------------------------

    --hcp_lowresmesh         ... The number of vertices to be used in the
                                 low-resolution grayordinate mesh (in thousands)
                                 [32].
    --hcp_bold_res           ... The resolution of the BOLD volume data in mm.
                                 [2]
    --hcp_grayordinatesres   ... The size of voxels for the subcortical and
                                 cerebellar data in grayordinate space in mm.
                                 [2]
    --hcp_bold_smoothFWHM    ... The size of the smoothing kernel (in mm). [2]
    --hcp_regname            ... The name of the registration used. []

    
    Full file checking
    ------------------

    If `--hcp_prefs_check` parameter is set to `all` or a specific file, after
    the completion of processing, the command will check whether processing was
    completed successfully by checking against a given file list. If 'all' is 
    specified, `check_fMRISurface.txt` file will be used, which has to be 
    present in the `<subjectsfolder>/subjects/specs` directory. If another 
    strings is given, the command will first check for a presence of a file with 
    such name in the spec folder (see before), and then check if it is a 
    valid path to a file. If a file is found, each line in a file should 
    represent a file or folder that has to be present in the 
    `<session id>/hcp/<session id>` directory. Folders should be separated by
    lines. Where a session id should be used, `{sessionid}` should be placed. 
    Where the actual bold name should be used '{scan} should be placed. These
    will be replaced with the actual session id and bold names at the time of 
    checking. 

    A line that starts with a '#' is considered a comment and will be ignored. 
    If two alternatives are possible and either one of them satisfies the check,
    they should be placed on the same line, separated by a '|' character.

    Example content:
    
    ```
    MNINonLinear Results {scan} {scan}.L.native.func.gii
    MNINonLinear Results {scan} {scan}.R.native.func.gii
    MNINonLinear Results {scan} {scan}_Atlas.dtseries.nii
    ```

    If full file checking is used:

    1/ the success of the run will be judged by the presence of all the files 
       as they are specified in the check file.
    2/ logs will be named:
       done        - the final file is present as well as all the required files
       incomplete  - the final file is present but not all the required files
       error       - the final file is missing
    3/ missing files will be printed to the stdout and a full report will be 
       appended to the log file.


    EXAMPLE USE
    ===========

    ```
    qunex hcp_fMRISurface sessions=fcMRI/subjects.hcp.txt subjectsfolder=subjects \\
          overwrite=no cores=10
    ```

    ```
    qunex hcp5 sessions=fcMRI/subjects.hcp.txt subjectsfolder=subjects \\
          overwrite=no cores=10
    ```

    ----------------
    Written by Grega Repovš

    Changelog
    2017-02-06 Grega Repovš
             - Updated documentation.
    2018-11-17 Jure Demsar
            - Parallel implementation.
    2018-12-14 Grega Repovš
            - FS Longitudinal implementation and documentation
    2019-01-12 Grega Repovš
             - Cleaned furher, added updates by Lisa Ji
    2019-04-25 Grega Repovš
             - Changed subjects to sessions
    2019-05-26 Grega Repovš
             - Added support for boldnamekey
             - Updated, simplified calling and testing
             - Added full file checking
    2019-06-06 Grega Repovš
             - Enabled multiple log file locations
    2019-10-20 Grega Repovš
             - Adjusted parameters, help and processing to use integrated HCPpipelines
    2020-01-05 Grega Repovš
             - Updated documentation
    '''

    r = "\n----------------------------------------------------------------"
    r += "\nSession id: %s \n[started on %s]" % (sinfo['id'], datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))
    r += "\n%s HCP fMRI Surface registration [%s] ..." % (action("Running", options['run']), options['hcp_processing_mode'])

    run    = True
    report = {'done': [], 'incomplete': [], 'failed': [], 'ready': [], 'not ready': [], 'skipped': []}

    try:

        # --- Base settings

        doOptionsCheck(options, sinfo, 'hcp_fMRISurface')
        doHCPOptionsCheck(options, sinfo, 'hcp_fMRISurface')
        hcp = getHCPPaths(sinfo, options)

        # --- bold filtering not yet supported!
        # btargets = options['bolds'].split("|")

        # --- run checks

        if 'hcp' not in sinfo:
            r += "\n---> ERROR: There is no hcp info for session %s in batch.txt" % (sinfo['id'])
            run = False

        # -> PostFS results

        if options['hcp_fs_longitudinal']:
            tfile = os.path.join(hcp['hcp_long_nonlin'], 'fsaverage_LR32k', sinfo['id'] + options['hcp_suffix'] + '.long.' + options['hcp_fs_longitudinal'] + '.32k_fs_LR.wb.spec')
        else:
            tfile = os.path.join(hcp['hcp_nonlin'], 'fsaverage_LR32k', sinfo['id'] + options['hcp_suffix'] + '.32k_fs_LR.wb.spec')

        if os.path.exists(tfile):
            r += "\n---> PostFS results present."
        else:
            r += "\n---> ERROR: Could not find PostFS processing results."
            if options['hcp_fs_longitudinal']:
                r += "\n--->        Please check that you have run PostFS on FS longitudinal as specified,"
                r += "\n--->        and that %s template was successfully used." % (options['hcp_fs_longitudinal'])
            run = False

        # --- Get sorted bold numbers

        bolds, bskip, report['boldskipped'], r = useOrSkipBOLD(sinfo, options, r)
        if report['boldskipped']:
            if options['hcp_filename'] == 'original':
                report['skipped'] = [bi.get('filename', str(bn)) for bn, bnm, bt, bi in bskip]
            else:
                report['skipped'] = [str(bn) for bn, bnm, bt, bi in bskip]

        threads = min(options['threads'], len(bolds))
        r += "\n\n%s BOLD images on %d threads" % (action("Processing", options['run']), threads)

        if threads == 1: # serial execution
            for b in bolds:
                # process
                result = executeHCPfMRISurface(sinfo, options, overwrite, hcp, run, b)

                # merge r
                r += result['r']

                # merge report
                tempReport            = result['report']
                report['done']       += tempReport['done']
                report['incomplete'] += tempReport['incomplete']
                report['failed']     += tempReport['failed']
                report['ready']      += tempReport['ready']
                report['not ready']  += tempReport['not ready']
                report['skipped']    += tempReport['skipped']

        else: # parallel execution
            # create a multiprocessing Pool
            processPoolExecutor = ProcessPoolExecutor(threads)
            # process 
            f = partial(executeHCPfMRISurface, sinfo, options, overwrite, hcp, run)
            results = processPoolExecutor.map(f, bolds)

            # merge r and report
            for result in results:
                r                    += result['r']
                tempReport            = result['report']
                report['done']       += tempReport['done']
                report['failed']     += tempReport['failed']
                report['incomplete'] += tempReport['incomplete']
                report['ready']      += tempReport['ready']
                report['not ready']  += tempReport['not ready']
                report['skipped']    += tempReport['skipped']
            
        rep = []
        for k in ['done', 'incomplete', 'failed', 'ready', 'not ready', 'skipped']:
            if len(report[k]) > 0:
                rep.append("%s %s" % (", ".join(report[k]), k))

        report = (sinfo['id'], "HCP fMRI Surface: bolds " + "; ".join(rep), len(report['failed'] + report['incomplete'] + report['not ready']))

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = str(errormessage)
        report = (sinfo['id'], 'HCP fMRI Surface failed')
    except:
        r += "\nERROR: Unknown error occured: \n...................................\n%s...................................\n" % (traceback.format_exc())
        report = (sinfo['id'], 'HCP fMRI Surface failed')

    r += "\n\nHCP fMRISurface %s on %s\n---------------------------------------------------------" % (action("completed", options['run']), datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))

    # print r
    return (r, report)


def executeHCPfMRISurface(sinfo, options, overwrite, hcp, run, boldData):
    # extract data
    bold, boldname, task, boldinfo = boldData

    if 'filename' in boldinfo and options['hcp_filename'] == 'original':
        printbold  = boldinfo['filename']
        boldsource = boldinfo['filename']
        boldtarget = boldinfo['filename']
    else:
        printbold  = str(bold)
        boldsource = 'BOLD_%d' % (bold)
        boldtarget = "%s%s" % (options['hcp_bold_prefix'], printbold)

    # prepare return variables
    r = ""
    report = {'done': [], 'incomplete': [], 'failed': [], 'ready': [], 'not ready': [], 'skipped': []}

    try:
        r += "\n\n---> %s BOLD image %s" % (action("Processing", options['run']), printbold)
        boldok = True

        # --- check for bold image
        boldimg = os.path.join(hcp['hcp_nonlin'], 'Results', boldtarget, "%s.nii.gz" % (boldtarget))
	print("BOLDIMG:  " + boldimg + os.linesep + os.linesep)
        r, boldok = checkForFile2(r, boldimg, '\n     ... fMRIVolume preprocessed bold image present', '\n     ... ERROR: fMRIVolume preprocessed bold image missing!', status=boldok)

        # --- Set up the command

        comm = os.path.join(hcp['hcp_base'], 'fMRISurface', 'GenericfMRISurfaceProcessingPipeline.sh') + " "

        elements = [('path',              sinfo['hcp']),
                    ('subject',           sinfo['id'] + options['hcp_suffix']),
                    ('fmriname',          boldtarget),
                    ('lowresmesh',        options['hcp_lowresmesh']),
                    ('fmrires',           options['hcp_bold_res']),
                    ('smoothingFWHM',     options['hcp_bold_smoothFWHM']),
                    ('grayordinatesres',  options['hcp_grayordinatesres']),
                    ('regname',           options['hcp_regname']),
                    ('printcom',          options['hcp_printcom'])]

        comm += " ".join(['--%s="%s"' % (k, v) for k, v in elements if v])


        # -- Test files

        if False:   # Longitudinal option currently not supported options['hcp_fs_longitudinal']:
            tfile = os.path.join(hcp['hcp_long_nonlin'], 'Results', "%s_%s" % (boldtarget, options['hcp_fs_longitudinal']), "%s_%s%s.dtseries.nii" % (boldtarget, options['hcp_fs_longitudinal'], options['hcp_cifti_tail']))
        else:
            tfile = os.path.join(hcp['hcp_nonlin'], 'Results', boldtarget, "%s%s.dtseries.nii" % (boldtarget, options['hcp_cifti_tail']))

        if hcp['hcp_bold_surf_check']:
            fullTest = {'tfolder': hcp['base'], 'tfile': hcp['hcp_bold_surf_check'], 'fields': [('sessionid', sinfo['id']), ('scan', boldtarget)], 'specfolder': options['specfolder']}
        else:
            fullTest = None

        # -- Run

        if run and boldok:
            if options['run'] == "run":
                if overwrite and os.path.exists(tfile):
                    os.remove(tfile)

                r, endlog, _, failed = runExternalForFile(tfile, comm, 'Running HCP fMRISurface', overwrite=overwrite, thread=sinfo['id'], remove=options['log'] == 'remove', task=options['command_ran'], logfolder=options['comlogs'], logtags=[options['logtag'], boldtarget], fullTest=fullTest, shell=True, r=r)

                if failed:
                    report['failed'].append(printbold)
                else:
                    report['done'].append(printbold)

            # -- just checking
            else:
                passed, _, r, failed = checkRun(tfile, fullTest, 'HCP fMRISurface ' + boldtarget, r)
                if passed is None:
                    r += "\n     ... HCP fMRISurface can be run"
                    r += "\n-----------------------------------------------------\nCommand to run:\n %s\n-----------------------------------------------------\n" % (comm.replace("--", "\n    --"))
                    report['ready'].append(printbold)
                else:
                    report['skipped'].append(printbold)

        elif run:
            report['not ready'].append(printbold)
            if options['run'] == "run":
                r += "\n     ... ERROR: images missing, skipping this BOLD!"
            else:
                r += "\n     ... ERROR: images missing, this BOLD would be skipped!"
        else:
            report['not ready'].append(printbold)
            if options['run'] == "run":
                r += "\n     ... ERROR: No hcp info for session, skipping this BOLD!"
            else:
                r += "\n     ... ERROR: No hcp info for session, this BOLD would be skipped!"

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = "\n\n\n --- Failed during processing of bold %s with error:\n" % (printbold)
        r += str(errormessage)
        report['failed'].append(printbold)
    except:
        r += "\n --- Failed during processing of bold %s with error:\n %s\n" % (printbold, traceback.format_exc())
        report['failed'].append(printbold)

    # r += "\n     ... DONE!"

    return {'r': r, 'report': report}


def parseICAFixBolds(options, bolds, r):
    # --- Use hcp_icafix_bolds parameter to determine if a single fix or a multi fix should be used
    singleFix = True
    # variable for storing groups and their bolds
    icafixGroups = {}

    if 'hcp_icafix_bolds' in options:
        icafixBolds = options['hcp_icafix_bolds']

        # if hcp_icafix_bolds includes : then we have groups and we need multi fix
        if ":" in icafixBolds:
            # run multi fix
            singleFix = False

            # get all groups
            groups = str.split(icafixBolds, "|")

            for g in groups:
                # get group name
                split = str.split(g, ":")

                # create group and add to dictionary
                icafixGroups[split[0]] = str.split(split[1], ",")

        # else we extract bolds and use single fix
        else:
            icafixBolds = str.split(icafixBolds, ",")
    # if hcp_icafix_bolds is empty then bundle all bolds
    else:
        icafixBolds = bolds
        icafixGroups = []
        icafixGroups.append({"name":"fMRI_CONCAT_ALL", "bolds":icafixBolds})

    # --- Report single fix or multi fix
    if singleFix:
        r += "\n\n%s single fix on %d bolds" % (action("Processing", options['run']), len(icafixBolds))
    else:
        r += "\n\n%s multi fix on %d groups" % (action("Processing", options['run']), len(icafixGroups))

    # --- Get hcp_icafix_bolds data from bolds
    # variable for storing skipped bolds
    boldSkip = {}

    if icafixBolds is not bolds:
        r += "\n%s bolds with hcp_icafix_bolds\n" % (action("Comparing", options['run']))
        # compare
        # single fix
        if singleFix:
            # variable for storing bold data
            boldData = []

            for icaB in icafixBolds:
                # find the bold in bolds
                found = False
                for b in bolds:
                    # extract data
                    _, _, _, boldinfo = b

                    if 'filename' in boldinfo and options['hcp_filename'] == 'original':
                        boldtarget = boldinfo['filename']
                    else:
                        boldtarget = "%s%s" % (options['hcp_bold_prefix'], printbold)

                    if icaB == boldtarget:
                        # add to temporary variable boldData
                        boldData.append(b)
                        found = True
                        boldSkip[boldtarget] = False
                        continue

                    if boldtarget not in boldSkip:
                        boldSkip[boldtarget] = True

            # store data into the icafixBolds variable
            icafixBolds = boldData
        # multi fix
        else:
            # variable for storing group data
            groupData = {}

            # go over all groups
            for g in icafixGroups:
                # create empty dict entry for group
                groupData[g] = []
                # go over group bolds
                groupBolds = icafixGroups[g]
                for groupB in groupBolds:
                    # look for bold in all bolds
                    found = False
                    for b in bolds:
                        # extract data
                        _, _, _, boldinfo = b

                        if 'filename' in boldinfo and options['hcp_filename'] == 'original':
                            boldtarget = boldinfo['filename']
                        else:
                            boldtarget = "%s%s" % (options['hcp_bold_prefix'], printbold)

                        if groupB == boldtarget:
                            # add bold to the group
                            groupData[g].append(b)
                            found = True
                            boldSkip[boldtarget] = False
                            continue

                        if boldtarget not in boldSkip:
                            boldSkip[boldtarget] = True

            # cast group data to array of dictionaries (needed for parallel)
            icafixGroups = []
            for g in groupData:
                icafixGroups.append({"name":g, "bolds":groupData[g]})

    # report hcp_icafix_bolds not found in bolds
    if len(boldSkip) > 0:
        for b in boldSkip:
            if boldSkip[b] is True:
                r += "     ... skipping %s: it is not specified in the hcp_icafix_bolds parameter\n" % b
    else:
        r += "     ... all bolds specified in the hcp_icafix_bolds parameter are present\n"


    return (singleFix, icafixBolds, icafixGroups, r)


def hcpICAFix(sinfo, options, overwrite=False, thread=0):
    '''
    hcp_ICAFix [... processing options]
    hcp6 [... processing options]

    USE
    ===

    A short name 'hcp6' can also be used for this command.

    Runs the ICAFix step of HCP Pipeline. This step attempts to auto-classify
    ICA components into good and bad components, so that the bad components
    can be then removed from the 4D FMRI data. If ICAFix step finishes
    successfully PostFix step will be ran automatically. 
    
    If the hcp_icafix_bolds parameter is not provided ICAFix will bundle
    all bolds together and execute multi-run HCP ICAFix, the concatenated file
    will be named fMRI_CONCAT_ALL. WARNING: if subject has many bolds such
    processing requires a lot of computational resources.

    REQUIREMENTS
    ============

    The code expects the input images to be named and present in the Qu|Nex
    folder structure. The function will look into folder:

    <session id>/hcp/<session id>

    for files:

    MNINonLinear/Results/<boldname>/<boldname>.nii.gz

    RESULTS
    =======

    The results of this step will be generated and populated in the
    MNINonLinear folder inside the same sessions's root hcp folder.

    The final clean ICA file can be found in:

    MNINonLinear/Results/<boldname>/<boldname>_hp<highpass>_clean.nii.gz,

    where highpass is the used value for the highpass filter. The default highpass
    value is 0 for multi-run HCP ICAFix and 2000 for single-run HCP ICAFix .


    RELEVANT PARAMETERS
    ===================

    general parameters
    ------------------

    --sessions          ... The batch.txt file with all the sessions information
                            [batch.txt].
    --subjectsfolder    ... The path to the study/subjects folder, where the
                            imaging  data is supposed to go [.].
    --cores             ... How many cores to utilize. This Parameter
                            determines the parallelization on the
                            subject level [1].
    --threads           ... How many threads to utilize This Parameter
                            determines the parallelization on the
                            bolds level [1].
    --overwrite         ... Whether to overwrite existing data (yes)
                            or not (no) [no].
    --logfolder         ... The path to the folder where runlogs and comlogs
                            are to be stored, if other than default []
    --log               ... Whether to keep ('keep') or remove ('remove') the
                            temporary logs once jobs are completed ['keep'].
                            When a comma separated list is given, the log will
                            be created at the first provided location and then
                            linked or copied to other locations. The valid
                            locations are:
                            * 'study'   for the default: 
                                        `<study>/processing/logs/comlogs`
                                        location,
                            * 'session' for `<sessionid>/logs/comlogs
                            * 'hcp'     for `<hcp_folder>/logs/comlogs
                            * '<path>'  for an arbitrary directory

    specific parameters
    -------------------

    In addition the following *specific* parameters will be used to guide the
    processing in this step:

    hcp_icafix_bolds                ... specify a list of bolds for ICAFix.
                                        You can specify a comma separated list
                                        of bolds, e.g. "<boldname1>,<boldname2>",
                                        in this case single-run HCP ICAFix will be
                                        executed over specified bolds. You can also
                                        specify how to group/concatenate bolds
                                        together, e.g.
                                        "<group1>:<boldname1>,<boldname2>|
                                        <group2>:<boldname3>,<boldname4>",
                                        in this case multi-run HCP ICAFix will be
                                        executed. If this parameter is not provided
                                        ICAFix will bundle all bolds together and
                                        execute multi-run HCP ICAFix, the
                                        concatenated file will be named
                                        fMRI_CONCAT_ALL [""].
    hcp_icafix_highpass             ... value for the highpass filter,
                                        [0] for multi-run HCP ICAFix and [2000]
                                        for single-run HCP ICAFix.
    hcp_matlab_mode                 ... Specifies the Matlab version, can be
                                        "interpreted", "compiled" or "octave"
                                        ["compiled"].
    hcp_icafix_domotionreg          ... Whether to regress motion parameters as
                                        part of the cleaning. The default value
                                        for single-run HCP ICAFix is ["TRUE"],
                                        while the default for multi-run HCP ICAFix
                                        is ["FALSE"].
    hcp_icafix_traindata            ... Which file to use for training data.
                                        You can provide a full path to a file or
                                        just a filename if the file is in the
                                        ${FSL_FIXDIR}/training_files folder.
                                        [""] for single-run HCP ICAFix and
                                        ["HCP_Style_Single_Multirun_Dedrift.RData"]
                                        for multi-run HCP ICAFix.
    hcp_icafix_threshold            ... ICAFix threshold that controls the
                                        sensitivity/specificity tradeoff [10].
    hcp_icafix_deleteintermediates  ... If TRUE, deletes both the concatenated
                                        high-pass filtered and non-filtered 
                                        timeseries files that are prerequisites
                                        to FIX cleaning ["FALSE"].

    EXAMPLE USE
    ===========
    
    ```
    qunex hcp_ICAFix \
        --sessions=processing/batch.txt \
        --subjectsfolder=subjects
    ```

    ```
    qunex hcp_ICAFix \
        --sessions=processing/batch.txt \
        --subjectsfolder=subjects \
        --hcp_icafix_bolds="GROUP_1:BOLD_1,BOLD_2|GROUP_2:BOLD_3,BOLD_4"
    ```

    ----------------
    Written by Jure Demšar

    Changelog
    2019-10-09 Jure Demsar
             - Core functionality.
    '''

    r = "\n----------------------------------------------------------------"
    r += "\nSession id: %s \n[started on %s]" % (sinfo['id'], datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))
    r += "\n%s HCP ICAFix registration [%s] ..." % (action("Running", options['run']), options['hcp_processing_mode'])

    run    = True
    report = {'done': [], 'incomplete': [], 'failed': [], 'ready': [], 'not ready': [], 'skipped': []}

    try:
        # --- Base settings
        doOptionsCheck(options, sinfo, 'hcp_ICAFix')
        doHCPOptionsCheck(options, sinfo, 'hcp_ICAFix')
        hcp = getHCPPaths(sinfo, options)

	print("hcp:  " + str(hcp))

        # --- Get sorted bold numbers and bold data
        bolds, bskip, report['boldskipped'], r = useOrSkipBOLD(sinfo, options, r)

	print("bolds:  " + str(bolds))
	print("bskip:  " + str(bskip))
	print("r:  " + str(r))
	print("report_boldskipped:  " + str(report['boldskipped']))

        if report['boldskipped']:
            if options['hcp_filename'] == 'original':
                report['skipped'] = [bi.get('filename', str(bn)) for bn, bnm, bt, bi in bskip]
            else:
                report['skipped'] = [str(bn) for bn, bnm, bt, bi in bskip]

        # --- Parse icafix_bolds
        singleFix, icafixBolds, icafixGroups, r = parseICAFixBolds(options, bolds, r)

	print("singleFix:  " + str(singleFix))
	print("icafixBolds:  " + str(icafixBolds))
	print("icafixGroups:  " + str(icafixGroups))

        # --- Multi threading
        threads = min(options['threads'], len(icafixBolds))
        r += "\n\n%s ICAFix on %d threads" % (action("Processing", options['run']), threads)

        # matlab run mode, compiled=0, interpreted=1, octave=2
        matlabrunmode = "0"
        if 'hcp_matlab_mode' in options:
            if options['hcp_matlab_mode'] == "compiled":
                matlabrunmode = "0"
            elif options['hcp_matlab_mode'] == "interpreted":
                matlabrunmode = "1"
            elif options['hcp_matlab_mode'] == "octave":
                matlabrunmode = "2"
            else:
                r += "\n     ... ERROR: wrong value for the hcp_matlab_mode parameter!"
                raise

        # set variable
        os.environ["FSL_FIX_MATLAB_MODE"] = matlabrunmode

        # --- Execute
        # single fix
        if singleFix:
            if threads == 1: # serial execution
                for b in icafixBolds:
                    # process
                    result = executeHCPSingleICAFix(sinfo, options, overwrite, hcp, run, b)

                    # merge r
                    r += result['r']

                    # merge report
                    tempReport            = result['report']
                    report['done']       += tempReport['done']
                    report['incomplete'] += tempReport['incomplete']
                    report['failed']     += tempReport['failed']
                    report['ready']      += tempReport['ready']
                    report['not ready']  += tempReport['not ready']
                    report['skipped']    += tempReport['skipped']

            else: # parallel execution
                # create a multiprocessing Pool
                processPoolExecutor = ProcessPoolExecutor(threads)
                # process 
                f = partial(executeHCPSingleICAFix, sinfo, options, overwrite, hcp, run)
                results = processPoolExecutor.map(f, icafixBolds)

                # merge r and report
                for result in results:
                    r                    += result['r']
                    tempReport            = result['report']
                    report['done']       += tempReport['done']
                    report['failed']     += tempReport['failed']
                    report['incomplete'] += tempReport['incomplete']
                    report['ready']      += tempReport['ready']
                    report['not ready']  += tempReport['not ready']
                    report['skipped']    += tempReport['skipped']

        # multi fix
        else: 
            if threads == 1: # serial execution
                for g in icafixGroups:
                    # process
                    result = executeHCPMultiICAFix(sinfo, options, overwrite, hcp, run, g)

                    # merge r
                    r += result['r']

                    # merge report
                    tempReport            = result['report']
                    report['done']       += tempReport['done']
                    report['incomplete'] += tempReport['incomplete']
                    report['failed']     += tempReport['failed']
                    report['ready']      += tempReport['ready']
                    report['not ready']  += tempReport['not ready']
                    report['skipped']    += tempReport['skipped'] 

            else: # parallel execution
                # create a multiprocessing Pool
                processPoolExecutor = ProcessPoolExecutor(threads)
                # process 
                f = partial(executeHCPMultiICAFix, sinfo, options, overwrite, hcp, run)
                results = processPoolExecutor.map(f, icafixGroups)

                # merge r and report
                for result in results:
                    r                    += result['r']
                    tempReport            = result['report']
                    report['done']       += tempReport['done']
                    report['failed']     += tempReport['failed']
                    report['incomplete'] += tempReport['incomplete']
                    report['ready']      += tempReport['ready']
                    report['not ready']  += tempReport['not ready']
                    report['skipped']    += tempReport['skipped']

        # report
        rep = []
        for k in ['done', 'incomplete', 'failed', 'ready', 'not ready', 'skipped']:
            if len(report[k]) > 0:
                rep.append("%s %s" % (", ".join(report[k]), k))

        report = (sinfo['id'], "HCP ICAFix: bolds " + "; ".join(rep), len(report['failed'] + report['incomplete'] + report['not ready']))

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = str(errormessage)
        report = (sinfo['id'], 'HCP ICAFix failed')
    except:
        r += "\nERROR: Unknown error occured: \n...................................\n%s...................................\n" % (traceback.format_exc())
        report = (sinfo['id'], 'HCP ICAFix failed')

    r += "\n\nHCP ICAFix %s on %s\n---------------------------------------------------------" % (action("completed", options['run']), datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))

    # print r
    return (r, report)


def executeHCPSingleICAFix(sinfo, options, overwrite, hcp, run, bold):
    # extract data
    _, _, _, boldinfo = bold

    if 'filename' in boldinfo and options['hcp_filename'] == 'original':
        printbold  = boldinfo['filename']
        boldtarget = boldinfo['filename']
    else:
        printbold  = str(bold)
        boldtarget = "%s%s" % (options['hcp_bold_prefix'], printbold)

    # prepare return variables
    r = ""
    report = {'done': [], 'incomplete': [], 'failed': [], 'ready': [], 'not ready': [], 'skipped': []}

    try:
        r += "\n\n----------------------------------------------------------------"
        r += "\n---> %s BOLD image %s" % (action("Processing", options['run']), printbold)
        boldok = True

        # --- check for bold image
        boldimg = os.path.join(hcp['hcp_nonlin'], 'Results', boldtarget, "%s.nii.gz" % (boldtarget))
	print("BOLDIMG:  " + boldimg + os.linesep + os.linesep)
        r, boldok = checkForFile2(r, boldimg, '\n     ... preprocessed bold image present', '\n     ... ERROR: preprocessed bold image missing!', status=boldok)

        # bold in input format
        inputfile = os.path.join(hcp['hcp_nonlin'], 'Results', boldtarget, "%s" % (boldtarget))

        # bandpass value
        bandpass = 2000 if 'hcp_icafix_highpass' not in options else options['hcp_icafix_highpass']

        comm = '%(script)s \
                "%(inputfile)s" \
                %(bandpass)d \
                "%(domot)s" \
                "%(trainingdata)s" \
                %(fixthreshold)d \
                "%(deleteintermediates)s"' % {
                'script'                : os.path.join(hcp['hcp_base'], 'ICAFIX', 'hcp_fix'),
                'inputfile'             : inputfile,
                'bandpass'              : bandpass,
                'domot'                 : "TRUE" if 'hcp_icafix_domotionreg' not in options else options['hcp_icafix_domotionreg'],
                'trainingdata'          : "" if 'hcp_icafix_traindata' not in options else options['hcp_icafix_traindata'],
                'fixthreshold'          : 10 if 'hcp_icafix_threshold' not in options else options['hcp_icafix_threshold'],
                'deleteintermediates'   : "FALSE" if 'hcp_icafix_deleteintermediates' not in options else options['hcp_icafix_deleteintermediates']}

        # -- Test file
        tfile = os.path.join(hcp['hcp_nonlin'], 'Results', boldtarget, "%s_hp%s_clean.nii.gz" % (boldtarget, bandpass))
        fullTest = None

        # -- Run
        if run and boldok:
            if options['run'] == "run":
                if overwrite and os.path.exists(tfile):
                    os.remove(tfile)

                r, endlog, _, failed = runExternalForFile(tfile, comm, 'Running single-run HCP ICAFix', overwrite=overwrite, thread=sinfo['id'], remove=options['log'] == 'remove', task=options['command_ran'], logfolder=options['comlogs'], logtags=[options['logtag'], boldtarget], fullTest=fullTest, shell=True, r=r)

                if failed:
                    report['failed'].append(printbold)
                else:
                    report['done'].append(printbold)

                # if all ok automatically execute PostFix
                if report['incomplete'] == [] and report['failed'] == [] and report['not ready'] == []:
                    result = executeHCPPostFix(sinfo, options, overwrite, hcp, run, True, bold)
                    r += result['r']
                    report = result['report']

            # -- just checking
            else:
                passed, _, r, failed = checkRun(tfile, fullTest, 'single-run HCP ICAFix ' + boldtarget, r)
                if passed is None:
                    r += "\n     ... single-run HCP ICAFix can be run"
                    r += "\n-----------------------------------------------------\nCommand to run:\n %s\n-----------------------------------------------------\n" % (comm.replace("--", "\n    --"))
                    report['ready'].append(printbold)
                else:
                    report['skipped'].append(printbold)

        elif run:
            report['not ready'].append(printbold)
            if options['run'] == "run":
                r += "\n     ... ERROR: images missing, skipping this BOLD!"
            else:
                r += "\n     ... ERROR: images missing, this BOLD would be skipped!"
        else:
            report['not ready'].append(printbold)
            if options['run'] == "run":
                r += "\n     ... ERROR: No hcp info for session, skipping this BOLD!"
            else:
                r += "\n     ... ERROR: No hcp info for session, this BOLD would be skipped!"

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = "\n\n\n --- Failed during processing of bold %s\n" % (printbold)
        r += str(errormessage)
        report['failed'].append(printbold)
    except:
        r += "\n --- Failed during processing of bold %s with error:\n %s\n" % (printbold, traceback.format_exc())
        report['failed'].append(printbold)

    return {'r': r, 'report': report}


def executeHCPMultiICAFix(sinfo, options, overwrite, hcp, run, group):
    # get group data
    groupname = group["name"]
    bolds = group["bolds"]

    # prepare return variables
    r = ""
    report = {'done': [], 'incomplete': [], 'failed': [], 'ready': [], 'not ready': [], 'skipped': []}

    try:
        r += "\n\n----------------------------------------------------------------"
        r += "\n---> %s group %s" % (action("Processing", options['run']), groupname)
        groupok = True

        # --- check for bold images and prepare images parameter
        boldimgs = ""

         # check if files for all bolds exist
        for b in bolds:
            # set ok to true for now
            boldok = True

            # extract data
            _, _, _, boldinfo = b

            if 'filename' in boldinfo and options['hcp_filename'] == 'original':
                printbold  = boldinfo['filename']
                boldtarget = boldinfo['filename']
            else:
                printbold  = str(bold)
                boldtarget = "%s%s" % (options['hcp_bold_prefix'], printbold)

            boldimg = os.path.join(hcp['hcp_nonlin'], 'Results', boldtarget, "%s" % (boldtarget))
            r, boldok = checkForFile2(r, "%s.nii.gz" % boldimg, '\n     ... bold image %s present' % boldtarget, '\n     ... ERROR: bold image [%s.nii.gz] missing!' % boldimg, status=boldok)

            if not boldok:
                groupok = False
                break
            else:
                # add @ separator
                if boldimgs is not "":
                    boldimgs = boldimgs + "@"

                # add latest image
                boldimgs = boldimgs + boldimg

        # construct concat file name
        concatfilename = os.path.join(hcp['hcp_nonlin'], 'Results', groupname, groupname)

        # bandpass
        bandpass = 0 if 'hcp_icafix_highpass' not in options else options['hcp_icafix_highpass']

        comm = '%(script)s \
                "%(inputfile)s" \
                %(bandpass)d \
                "%(concatfilename)s" \
                "%(domot)s" \
                "%(trainingdata)s" \
                %(fixthreshold)d \
                "%(deleteintermediates)s"' % {
                'script'                : os.path.join(hcp['hcp_base'], 'ICAFIX', 'hcp_fix_multi_run'),
                'inputfile'             : boldimgs,
                'bandpass'              : bandpass,
                'concatfilename'        : concatfilename,
                'domot'                 : "FALSE" if 'hcp_icafix_domotionreg' not in options else options['hcp_icafix_domotionreg'],
                'trainingdata'          : "HCP_Style_Single_Multirun_Dedrift.RData" if 'hcp_icafix_traindata' not in options else options['hcp_icafix_traindata'],
                'fixthreshold'          : 10 if 'hcp_icafix_threshold' not in options else options['hcp_icafix_threshold'],
                'deleteintermediates'   : "FALSE" if 'hcp_icafix_deleteintermediates' not in options else options['hcp_icafix_deleteintermediates']}

        # -- Test file
        tfile = concatfilename + "_hp%s_clean.nii.gz" % bandpass
        fullTest = None

        # -- Run
        if run and groupok:
            if options['run'] == "run":
                if overwrite and os.path.exists(tfile):
                    os.remove(tfile)

                r, endlog, _, failed = runExternalForFile(tfile, comm, 'Running multi-run HCP ICAFix', overwrite=overwrite, thread=sinfo['id'], remove=options['log'] == 'remove', task=options['command_ran'], logfolder=options['comlogs'], logtags=[options['logtag'], groupname], fullTest=fullTest, shell=True, r=r)

                if failed:
                    report['failed'].append(groupname)
                else:
                    report['done'].append(groupname)

                # if all ok automatically execute PostFix
                if report['incomplete'] == [] and report['failed'] == [] and report['not ready'] == []:
                    result = executeHCPPostFix(sinfo, options, overwrite, hcp, run, False, groupname)
                    r += result['r']
                    report = result['report']

            # -- just checking
            else:
                passed, _, r, failed = checkRun(tfile, fullTest, 'multi-run HCP ICAFix ' + groupname, r)
                if passed is None:
                    r += "\n     ... multi-run HCP ICAFix can be run"
                    r += "\n-----------------------------------------------------\nCommand to run:\n %s\n-----------------------------------------------------\n" % (comm.replace("--", "\n    --"))
                    report['ready'].append(groupname)
                else:
                    report['skipped'].append(groupname)

        elif run:
            report['not ready'].append(groupname)
            if options['run'] == "run":
                r += "\n     ... ERROR: images missing, skipping this group!"
            else:
                r += "\n     ... ERROR: images missing, this group would be skipped!"
        else:
            report['not ready'].append(groupname)
            if options['run'] == "run":
                r += "\n     ... ERROR: No Workbench scene files that can be used to visually review the signal vs. noise classification generated by ICAFix, skipping this group!"
            else:
                r += "\n     ... ERROR: No Workbench scene files that can be used to visually review the signal vs. noise classification generated by ICAFix, this group would be skipped!"

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = "\n\n\n --- Failed during processing of group %s with error:\n" % (groupname)
        r += str(errormessage)
        report['failed'].append(groupname)
    except:
        r += "\n --- Failed during processing of group %s with error:\n %s\n" % (groupname, traceback.format_exc())
        report['failed'].append(groupname)

    return {'r': r, 'report': report}


def hcpPostFix(sinfo, options, overwrite=False, thread=0):
    '''
    hcp_PostFix [... processing options]
    hcp7 [... processing options]

    USE
    ===

    A short name 'hcp7' can also be used for this command.

    Runs the PostFix step of HCP Pipeline. This step creates Workbench scene
    files that can be used to visually review the signal vs. noise
    classification generated by ICAFix.

    If the hcp_icafix_bolds parameter is not provided ICAFix will bundle
    all bolds together and execute multi-run HCP ICAFix, the concatenated file
    will be named fMRI_CONCAT_ALL. WARNING: if subject has many bolds such
    processing requires a lot of computational resources.

    REQUIREMENTS
    ============

    The code expects the input images to be named and present in the Qu|Nex
    folder structure. The function will look into folder:

    <session id>/hcp/<session id>

    for files:

    MNINonLinear/Results/<boldname>/<boldname>_hp<highpass>_clean.nii.gz

    RESULTS
    =======

    The results of this step will be generated and populated in the
    MNINonLinear folder inside the same sessions's root hcp folder.

    The final output files are:

    MNINonLinear/Results/<boldname>/
    <session id>_<boldname>_hp<highpass>_ICA_Classification_singlescreen.scene,

    where highpass is the used value for the highpass filter. The default highpass
    value is 0 for multi-run HCP ICAFix and 2000 for single-run HCP ICAFix .

    RELEVANT PARAMETERS
    ===================

    general parameters
    ------------------

    --sessions          ... The batch.txt file with all the sessions information
                            [batch.txt].
    --subjectsfolder    ... The path to the study/subjects folder, where the
                            imaging  data is supposed to go [.].
    --cores             ... How many cores to utilize. This Parameter
                            determines the parallelization on the
                            subject level [1].
    --threads           ... How many threads to utilize This Parameter
                            determines the parallelization on the
                            bolds level [1].
    --overwrite         ... Whether to overwrite existing data (yes)
                            or not (no) [no].
    --logfolder         ... The path to the folder where runlogs and comlogs
                            are to be stored, if other than default []
    --log               ... Whether to keep ('keep') or remove ('remove') the
                            temporary logs once jobs are completed ['keep'].
                            When a comma separated list is given, the log will
                            be created at the first provided location and then
                            linked or copied to other locations. The valid
                            locations are:
                            * 'study'   for the default: 
                                        `<study>/processing/logs/comlogs`
                                        location,
                            * 'session' for `<sessionid>/logs/comlogs
                            * 'hcp'     for `<hcp_folder>/logs/comlogs
                            * '<path>'  for an arbitrary directory

    specific parameters
    -------------------

    In addition the following *specific* parameters will be used to guide the
    processing in this step:

    hcp_icafix_bolds            ... specify a list of bolds for ICAFix.
                                    You can specify a comma separated list
                                    of bolds, e.g. "<boldname1>,<boldname2>",
                                    in this case single-run HCP ICAFix will be
                                    executed over specified bolds. You can also
                                    specify how to group/concatenate bolds
                                    together, e.g.
                                    "<group1>:<boldname1>,<boldname2>|
                                    <group2>:<boldname3>,<boldname4>",
                                    in this case multi-run HCP ICAFix will be
                                    executed. If this parameter is not provided
                                    ICAFix will bundle all bolds together and
                                    execute multi-run HCP ICAFix, the
                                    concatenated file will be named
                                    fMRI_CONCAT_ALL [""].
    hcp_icafix_highpass         ... value for the highpass filter,
                                    [0] for multi-run HCP ICAFix and [2000]
                                    for single-run HCP ICAFix.
    hcp_matlab_mode             ... Specifies the Matlab version, can be
                                    "interpreted", "compiled" or "octave"
                                    ["compiled"].
    hcp_postfix_dualscene       ... Path to an alternative template scene, if
                                    empty HCP default dual scene will be used
                                    [""].
    hcp_postfix_singlescene     ... Path to an alternative template scene, if
                                    empty HCP default single scene will be used
                                    [""].
    hcp_postfix_reusehighpass   ... Whether to reuse highpass ["YES"].


    EXAMPLE USE
    ===========
    
    ```
    qunex hcp_PostFix \
        --sessions=processing/batch.txt \
        --subjectsfolder=subjects \
        --hcp_matlab_mode="interpreted"
    ```

    ```
    qunex hcp_PostFix \
        --sessions=processing/batch.txt \
        --subjectsfolder=subjects \
        --hcp_icafix_bolds="GROUP_1:BOLD_1,BOLD_2|GROUP_2:BOLD_3,BOLD_4" \
        --hcp_matlab_mode="interpreted"
    ```


    ----------------
    Written by Jure Demšar

    Changelog
    2019-10-11 Jure Demsar
             - Core functionality.
    '''

    r = "\n----------------------------------------------------------------"
    r += "\nSession id: %s \n[started on %s]" % (sinfo['id'], datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))
    r += "\n%s HCP PostFix registration [%s] ..." % (action("Running", options['run']), options['hcp_processing_mode'])

    run    = True
    report = {'done': [], 'incomplete': [], 'failed': [], 'ready': [], 'not ready': [], 'skipped': []}

    try:
        # --- Base settings
        doOptionsCheck(options, sinfo, 'hcp_PostFix')
        doHCPOptionsCheck(options, sinfo, 'hcp_PostFix')
        hcp = getHCPPaths(sinfo, options)

        # --- Get sorted bold numbers and bold data
        bolds, bskip, report['boldskipped'], r = useOrSkipBOLD(sinfo, options, r)
        if report['boldskipped']:
            if options['hcp_filename'] == 'original':
                report['skipped'] = [bi.get('filename', str(bn)) for bn, bnm, bt, bi in bskip]
            else:
                report['skipped'] = [str(bn) for bn, bnm, bt, bi in bskip]

        # --- Parse icafix_bolds
        singleFix, icafixBolds, icafixGroups, r = parseICAFixBolds(options, bolds, r)

        # --- Multi threading
        threads = min(options['threads'], len(icafixBolds))
        r += "\n\n%s PostFix on %d threads" % (action("Processing", options['run']), threads)

        # --- Execute
        # single fix
        if not singleFix:
            # put all group bolds together
            icafixBolds = []
            for g in icafixGroups:
                groupBolds = g["name"]
                icafixBolds.append(groupBolds)

        if threads == 1: # serial execution
            for b in icafixBolds:
                # process
                result = executeHCPPostFix(sinfo, options, overwrite, hcp, run, singleFix, b)

                # merge r
                r += result['r']

                # merge report
                tempReport            = result['report']
                report['done']       += tempReport['done']
                report['incomplete'] += tempReport['incomplete']
                report['failed']     += tempReport['failed']
                report['ready']      += tempReport['ready']
                report['not ready']  += tempReport['not ready']
                report['skipped']    += tempReport['skipped']

        else: # parallel execution
            # create a multiprocessing Pool
            processPoolExecutor = ProcessPoolExecutor(threads)
            # process 
            f = partial(executeHCPPostFix, sinfo, options, overwrite, hcp, run, singleFix)
            results = processPoolExecutor.map(f, icafixBolds)

            # merge r and report
            for result in results:
                r                    += result['r']
                tempReport            = result['report']
                report['done']       += tempReport['done']
                report['failed']     += tempReport['failed']
                report['incomplete'] += tempReport['incomplete']
                report['ready']      += tempReport['ready']
                report['not ready']  += tempReport['not ready']
                report['skipped']    += tempReport['skipped']
        
        # report
        rep = []
        for k in ['done', 'incomplete', 'failed', 'ready', 'not ready', 'skipped']:
            if len(report[k]) > 0:
                rep.append("%s %s" % (", ".join(report[k]), k))

        report = (sinfo['id'], "HCP PostFix: bolds " + "; ".join(rep), len(report['failed'] + report['incomplete'] + report['not ready']))

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = str(errormessage)
        report = (sinfo['id'], 'HCP PostFix failed')
    except:
        r += "\nERROR: Unknown error occured: \n...................................\n%s...................................\n" % (traceback.format_exc())
        report = (sinfo['id'], 'HCP PostFix failed')

    r += "\n\nHCP PostFix %s on %s\n---------------------------------------------------------" % (action("completed", options['run']), datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))

    # print r
    return (r, report)


def executeHCPPostFix(sinfo, options, overwrite, hcp, run, singleFix, bold):
    # prepare return variables
    r = ""
    report = {'done': [], 'incomplete': [], 'failed': [], 'ready': [], 'not ready': [], 'skipped': []}

    # extract data
    r += "\n\n----------------------------------------------------------------"

    if singleFix:
        # highpass
        highpass = 2000 if 'hcp_icafix_highpass' not in options else options['hcp_icafix_highpass']

        _, _, _, boldinfo = bold

        if 'filename' in boldinfo and options['hcp_filename'] == 'original':
            printbold  = boldinfo['filename']
            boldtarget = boldinfo['filename']
        else:
            printbold  = str(bold)
            boldtarget = "%s%s" % (options['hcp_bold_prefix'], printbold)

        printica = "%s_hp%s_clean.nii.gz" % (boldtarget, highpass)
        icaimg = os.path.join(hcp['hcp_nonlin'], 'Results', boldtarget, printica)
        r += "\n---> %s bold ICA %s" % (action("Processing", options['run']), printica)

    else:
        # highpass
        highpass = 0 if 'hcp_icafix_highpass' not in options else options['hcp_icafix_highpass']

        printbold = bold
        boldtarget = bold

        printica = "%s_hp%s_clean.nii.gz" % (boldtarget, highpass)
        icaimg = os.path.join(hcp['hcp_nonlin'], 'Results', boldtarget, printica)
        r += "\n---> %s group ICA %s" % (action("Processing", options['run']), printica)

    try:
        boldok = True

        # --- check for ICA image
        r, boldok = checkForFile2(r, icaimg, '\n     ... preprocessed ICA present', '\n     ... ERROR: preprocessed ICA missing!', status=boldok)

        reusehighpass = "YES" if 'hcp_postfix_reusehighpass' not in options else options['hcp_postfix_reusehighpass']

        singlescene = os.path.join(hcp['hcp_base'], 'ICAFIX/PostFixScenes/', 'ICA_Classification_SingleScreenTemplate.scene')
        if 'hcp_postfix_singlescene' in options:
            singlescene = options['hcp_postfix_singlescene']

        dualscene = os.path.join(hcp['hcp_base'], 'ICAFIX/PostFixScenes/', 'ICA_Classification_DualScreenTemplate.scene')
        if 'hcp_postfix_dualscene' in options:
            dualscene = options['hcp_postfix_dualscene']

        # matlab run mode, compiled=0, interpreted=1, octave=2
        matlabrunmode = 0
        if 'hcp_matlab_mode' in options:
            if options['hcp_matlab_mode'] == "compiled":
                matlabrunmode = 0
            elif options['hcp_matlab_mode'] == "interpreted":
                matlabrunmode = 1
            elif options['hcp_matlab_mode'] == "octave":
                matlabrunmode = 2
            else:
                r += "\n     ... ERROR: wrong value for the hcp_matlab_mode parameter!"
                boldok = False

        # subject
        subject = sinfo['id'] + options['hcp_suffix']

        comm = '%(script)s \
            --study-folder="%(studyfolder)s" \
            --subject="%(subject)s" \
            --fmri-name="%(boldtarget)s" \
            --high-pass="%(highpass)d" \
            --template-scene-dual-screen="%(dualscene)s" \
            --template-scene-single-screen="%(singlescene)s" \
            --reuse-high-pass="%(reusehighpass)s" \
            --matlab-run-mode="%(matlabrunmode)d"' % {
                'script'            : os.path.join(hcp['hcp_base'], 'ICAFIX', 'PostFix.sh'),
                'studyfolder'       : sinfo['hcp'],
                'subject'           : subject,
                'boldtarget'        : boldtarget,
                'highpass'          : highpass,
                'dualscene'         : dualscene,
                'singlescene'       : singlescene,
                'reusehighpass'     : reusehighpass,
                'matlabrunmode'     : matlabrunmode}

        # -- Test files
        tfile = os.path.join(hcp['hcp_nonlin'], 'Results', boldtarget, "%s_%s_hp%s_ICA_Classification_singlescreen.scene" % (subject, boldtarget, highpass))
        fullTest = None

        # -- Run
        if run and boldok:
            if options['run'] == "run":
                if overwrite and os.path.exists(tfile):
                    os.remove(tfile)

                r, endlog, _, failed = runExternalForFile(tfile, comm, 'Running HCP PostFix', overwrite=overwrite, thread=sinfo['id'], remove=options['log'] == 'remove', task="hcp_PostFix", logfolder=options['comlogs'], logtags=[options['logtag'], boldtarget], fullTest=fullTest, shell=True, r=r)

                if failed:
                    report['failed'].append(printbold)
                else:
                    report['done'].append(printbold)

            # -- just checking
            else:
                passed, _, r, failed = checkRun(tfile, fullTest, 'HCP PostFix ' + boldtarget, r)
                if passed is None:
                    r += "\n     ... HCP PostFix can be run"
                    r += "\n-----------------------------------------------------\nCommand to run:\n %s\n-----------------------------------------------------\n" % (comm.replace("--", "\n    --"))
                    report['ready'].append(printbold)
                else:
                    report['skipped'].append(printbold)

        elif run:
            report['not ready'].append(printbold)
            if options['run'] == "run":
                r += "\n     ... ERROR: images missing, skipping this BOLD!"
            else:
                r += "\n     ... ERROR: images missing, this BOLD would be skipped!"
        else:
            report['not ready'].append(printbold)
            if options['run'] == "run":
                r += "\n     ... ERROR: No hcp info for session, skipping this BOLD!"
            else:
                r += "\n     ... ERROR: No hcp info for session, this BOLD would be skipped!"

        # log beautify
        r += "\n\n"

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = "\n\n\n --- Failed during processing of bold %s with error:\n" % (printbold)
        r += str(errormessage)
        report['failed'].append(printbold)
    except:
        r += "\n --- Failed during processing of bold %s with error:\n %s\n" % (printbold, traceback.format_exc())
        report['failed'].append(printbold)

    return {'r': r, 'report': report}


def hcpReApplyFix(sinfo, options, overwrite=False, thread=0):
    '''
    hcp_ReApplyFix [... processing options]
    hcp8 [... processing options]

    USE
    ===

    A short name 'hcp8' can also be used for this command.

    Runs the ReApplyFix step of HCP Pipeline. This function executes two steps,
    first it applies the hand reclassifications of noise and signal components
    from FIX using the ReclassifyAsNoise.txt and ReclassifyAsSignal.txt input
    files. Next it executes the HCP Pipeline's ReApplyFix or ReApplyFixMulti.

    If the hcp_icafix_bolds parameter is not provided ICAFix will bundle
    all bolds together and execute multi-run HCP ICAFix, the concatenated file
    will be named fMRI_CONCAT_ALL. WARNING: if subject has many bolds such
    processing requires a lot of computational resources.

    REQUIREMENTS
    ============

    The code expects the input images to be named and present in the Qu|Nex
    folder structure. The function will look into folder:

    <session id>/hcp/<session id>

    for files:

    MNINonLinear/Results/<boldname>/<boldname>.nii.gz

    RESULTS
    =======

    The results of this step will be generated and populated in the
    MNINonLinear folder inside the same sessions's root hcp folder.

    The final clean ICA file can be found in:

    MNINonLinear/Results/<boldname>/<boldname>_hp<highpass>_clean.nii.gz,

    where highpass is the used value for the highpass filter. The default highpass
    value is 0 for multi-run HCP ICAFix and 2000 for single-run HCP ICAFix .

    RELEVANT PARAMETERS
    ===================

    general parameters
    ------------------

    --sessions          ... The batch.txt file with all the sessions information
                            [batch.txt].
    --subjectsfolder    ... The path to the study/subjects folder, where the
                            imaging  data is supposed to go [.].
    --cores             ... How many cores to utilize. This Parameter
                            determines the parallelization on the
                            subject level [1].
    --threads           ... How many threads to utilize This Parameter
                            determines the parallelization on the
                            bolds level [1].
    --overwrite         ... Whether to overwrite existing data (yes)
                            or not (no) [no].
    --logfolder         ... The path to the folder where runlogs and comlogs
                            are to be stored, if other than default []
    --log               ... Whether to keep ('keep') or remove ('remove') the
                            temporary logs once jobs are completed ['keep'].
                            When a comma separated list is given, the log will
                            be created at the first provided location and then
                            linked or copied to other locations. The valid
                            locations are:
                            * 'study'   for the default: 
                                        `<study>/processing/logs/comlogs`
                                        location,
                            * 'session' for `<sessionid>/logs/comlogs
                            * 'hcp'     for `<hcp_folder>/logs/comlogs
                            * '<path>'  for an arbitrary directory

    specific parameters
    -------------------

    In addition the following *specific* parameters will be used to guide the
    processing in this step:

    hcp_icafix_bolds                ... specify a list of bolds for ICAFix.
                                        You can specify a comma separated list
                                        of bolds, e.g. "<boldname1>,<boldname2>",
                                        in this case single-run HCP ICAFix will be
                                        executed over specified bolds. You can also
                                        specify how to group/concatenate bolds
                                        together, e.g.
                                        "<group1>:<boldname1>,<boldname2>|
                                        <group2>:<boldname3>,<boldname4>",
                                        in this case multi-run HCP ICAFix will be
                                        executed. If this parameter is not provided
                                        ICAFix will bundle all bolds together and
                                        execute multi-run HCP ICAFix, the
                                        concatenated file will be named
                                        fMRI_CONCAT_ALL [""].
    hcp_icafix_highpass             ... value for the highpass filter,
                                        [0] for multi-run HCP ICAFix and [2000]
                                        for single-run HCP ICAFix.
    hcp_matlab_mode                 ... Specifies the Matlab version, can be
                                        "interpreted", "compiled" or "octave"
                                        ["compiled"].
    hcp_icafix_domotionreg          ... Whether to regress motion parameters as
                                        part of the cleaning. The default value
                                        for single-run HCP ICAFix is ["TRUE"],
                                        while the default for multi-run HCP ICAFix
                                        is ["FALSE"].
    hcp_icafix_deleteintermediates  ... If TRUE, deletes both the concatenated
                                        high-pass filtered and non-filtered 
                                        timeseries files that are prerequisites
                                        to FIX cleaning ["FALSE"].
    hcp_regname                     ... Specifies surface registration name
                                        ["NONE"].
    hcp_lowresmesh                  ... Specifies the low res mesh number [32].

    EXAMPLE USE
    ===========
    
    ```
    qunex hcp_ReApplyFix \
        --sessions=processing/batch.txt \
        --subjectsfolder=subjects \
        --hcp_matlab_mode="interpreted"
    ```

    ```
    qunex hcp_ReApplyFix \
        --sessions=processing/batch.txt \
        --subjectsfolder=subjects \
        --hcp_icafix_bolds="GROUP_1:BOLD_1,BOLD_2|GROUP_2:BOLD_3,BOLD_4" \
        --hcp_matlab_mode="interpreted"
    ```

    ----------------
    Written by Jure Demšar

    Changelog
    2019-10-15 Jure Demsar
             - Core functionality.
    '''

    r = "\n----------------------------------------------------------------"
    r += "\nSession id: %s \n[started on %s]" % (sinfo['id'], datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))
    r += "\n%s HCP ReApplyFix registration [%s] ..." % (action("Running", options['run']), options['hcp_processing_mode'])

    run    = True
    report = {'done': [], 'incomplete': [], 'failed': [], 'ready': [], 'not ready': [], 'skipped': []}

    try:
        # --- Base settings
        doOptionsCheck(options, sinfo, 'hcp_ReApplyFix')
        doHCPOptionsCheck(options, sinfo, 'hcp_ReApplyFix')
        hcp = getHCPPaths(sinfo, options)

        # --- Get sorted bold numbers and bold data
        bolds, bskip, report['boldskipped'], r = useOrSkipBOLD(sinfo, options, r)
        if report['boldskipped']:
            if options['hcp_filename'] == 'original':
                report['skipped'] = [bi.get('filename', str(bn)) for bn, bnm, bt, bi in bskip]
            else:
                report['skipped'] = [str(bn) for bn, bnm, bt, bi in bskip]

        # --- Parse icafix_bolds
        singleFix, icafixBolds, icafixGroups, r = parseICAFixBolds(options, bolds, r)

        # --- Multi threading
        threads = min(options['threads'], len(icafixBolds))
        r += "\n\n%s ReApplyFix on %d threads" % (action("Processing", options['run']), threads)

        # --- Execute
        # single fix
        if singleFix:
            if threads == 1: # serial execution
                for b in icafixBolds:
                    # process
                    result = executeHCPSingleReApplyFix(sinfo, options, overwrite, hcp, run, b)

                    # merge r
                    r += result['r']

                    # merge report
                    tempReport            = result['report']
                    report['done']       += tempReport['done']
                    report['incomplete'] += tempReport['incomplete']
                    report['failed']     += tempReport['failed']
                    report['ready']      += tempReport['ready']
                    report['not ready']  += tempReport['not ready'] 
                    report['skipped']    += tempReport['skipped']

            else: # parallel execution
                # create a multiprocessing Pool
                processPoolExecutor = ProcessPoolExecutor(threads)
                # process 
                f = partial(executeHCPSingleReApplyFix, sinfo, options, overwrite, hcp, run)
                results = processPoolExecutor.map(f, icafixBolds)

                # merge r and report
                for result in results:
                    r                    += result['r']
                    tempReport            = result['report']
                    report['done']       += tempReport['done']
                    report['failed']     += tempReport['failed']
                    report['incomplete'] += tempReport['incomplete']
                    report['ready']      += tempReport['ready']
                    report['not ready']  += tempReport['not ready']
                    report['skipped']    += tempReport['skipped']

        # multi fix
        else: 
            if threads == 1: # serial execution
                for g in icafixGroups:
                    # process
                    result = executeHCPMultiReApplyFix(sinfo, options, overwrite, hcp, run, g)

                    # merge r
                    r += result['r']

                    # merge report
                    tempReport            = result['report']
                    report['done']       += tempReport['done']
                    report['incomplete'] += tempReport['incomplete']
                    report['failed']     += tempReport['failed']
                    report['ready']      += tempReport['ready']
                    report['not ready']  += tempReport['not ready']
                    report['skipped']    += tempReport['skipped']

            else: # parallel execution
                # create a multiprocessing Pool
                processPoolExecutor = ProcessPoolExecutor(threads)
                # process 
                f = partial(executeHCPMultiReApplyFix, sinfo, options, overwrite, hcp, run)
                results = processPoolExecutor.map(f, icafixGroups)

                # merge r and report
                for result in results:
                    r                    += result['r']
                    tempReport            = result['report']
                    report['done']       += tempReport['done']
                    report['failed']     += tempReport['failed']
                    report['incomplete'] += tempReport['incomplete']
                    report['ready']      += tempReport['ready']
                    report['not ready']  += tempReport['not ready']
                    report['skipped']    += tempReport['skipped']

        # report
        rep = []
        for k in ['done', 'incomplete', 'failed', 'ready', 'not ready', 'skipped']:
            if len(report[k]) > 0:
                rep.append("%s %s" % (", ".join(report[k]), k))

        report = (sinfo['id'], "HCP ReApplyFix: bolds " + "; ".join(rep), len(report['failed'] + report['incomplete'] + report['not ready']))

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = str(errormessage)
        report = (sinfo['id'], 'HCP ReApplyFix failed')
    except:
        r += "\nERROR: Unknown error occured: \n...................................\n%s...................................\n" % (traceback.format_exc())
        report = (sinfo['id'], 'HCP ReApplyFix failed')

    r += "\n\nHCP ReApplyFix %s on %s\n---------------------------------------------------------" % (action("completed", options['run']), datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))

    # print r
    return (r, report)


def executeHCPSingleReApplyFix(sinfo, options, overwrite, hcp, run, bold):
    # extract data
    _, _, _, boldinfo = bold

    if 'filename' in boldinfo and options['hcp_filename'] == 'original':
        printbold  = boldinfo['filename']
        boldtarget = boldinfo['filename']
    else:
        printbold  = str(bold)
        boldtarget = "%s%s" % (options['hcp_bold_prefix'], printbold)

    # prepare return variables
    r = ""
    report = {'done': [], 'incomplete': [], 'failed': [], 'ready': [], 'not ready': [], 'skipped': []}

    try:
        # run HCP hand reclassification
        r += "\n----------------------------------------------------------------"
        r += "\n---> Executing HCP Hand reclassification for bold: %s\n" % printbold
        result = executeHCPHandReclassification(sinfo, options, overwrite, hcp, run, True, boldtarget, printbold)

        # merge r
        r += result['r']

        # move on to ReApplyFix
        rcReport = result['report']
        if rcReport['incomplete'] == [] and rcReport['failed'] == [] and rcReport['not ready'] == []:
            boldok = True

            # highpass
            highpass = 2000 if 'hcp_icafix_highpass' not in options else options['hcp_icafix_highpass']

            # matlab run mode, compiled=0, interpreted=1, octave=2
            matlabrunmode = 0
            if 'hcp_matlab_mode' in options:
                if options['hcp_matlab_mode'] == "compiled":
                    matlabrunmode = 0
                elif options['hcp_matlab_mode'] == "interpreted":
                    matlabrunmode = 1
                elif options['hcp_matlab_mode'] == "octave":
                    matlabrunmode = 2
                else:
                    r += "\n     ... ERROR: wrong value for the hcp_matlab_mode parameter!"
                    boldok = False

            # regname
            regname = "NONE"
            if 'hcp_regname' not in options or options['hcp_regname'] != "":
                regname = options['hcp_regname']

            comm = '%(script)s \
                --path="%(path)s" \
                --subject="%(subject)s" \
                --fmri-name="%(boldtarget)s" \
                --high-pass="%(highpass)d" \
                --reg-name="%(regname)s" \
                --low-res-mesh="%(lowresmesh)d" \
                --matlab-run-mode="%(matlabrunmode)d" \
                --motion-regression="%(motionregression)s" \
                --delete-intermediates="%(deleteintermediates)s"' % {
                    'script'              : os.path.join(hcp['hcp_base'], 'ICAFIX', 'ReApplyFixPipeline.sh'),
                    'path'                : sinfo['hcp'],
                    'subject'             : sinfo['id'] + options['hcp_suffix'],
                    'boldtarget'          : boldtarget,
                    'highpass'            : highpass,
                    'regname'             : regname,
                    'lowresmesh'          : 32 if 'hcp_lowresmesh' not in options else options['hcp_lowresmesh'],
                    'matlabrunmode'       : matlabrunmode,
                    'motionregression'    : "FALSE" if 'hcp_icafix_domotionreg' not in options else options['hcp_icafix_domotionreg'],
                    'deleteintermediates' : "FALSE" if 'hcp_icafix_deleteintermediates' not in options else options['hcp_icafix_deleteintermediates']}

            # -- Test files
            # postfix
            postfix = "%s%s_hp%s_clean.dtseries.nii" % (boldtarget, options['hcp_cifti_tail'], highpass)
            if regname != "NONE":
                postfix = "%s%s_%s_hp%s_clean.dtseries.nii" % (boldtarget, options['hcp_cifti_tail'], regname, highpass)

            tfile = os.path.join(hcp['hcp_nonlin'], 'Results', boldtarget, postfix)
            fullTest = None

            # -- Run
            if run and boldok:
                if options['run'] == "run":
                    r, endlog, _, failed = runExternalForFile(tfile, comm, 'Running single-run HCP ReApplyFix', overwrite=overwrite, thread=sinfo['id'], remove=options['log'] == 'remove', task=options['command_ran'], logfolder=options['comlogs'], logtags=[options['logtag'], boldtarget], fullTest=fullTest, shell=True, r=r)

                    if failed:
                        report['failed'].append(printbold)
                    else:
                        report['done'].append(printbold)

                # -- just checking
                else:
                    passed, _, r, failed = checkRun(tfile, fullTest, 'single-run HCP ReApplyFix ' + boldtarget, r)
                    if passed is None:
                        r += "\n     ... single-run HCP ReApplyFix can be run"
                        r += "\n-----------------------------------------------------\nCommand to run:\n %s\n-----------------------------------------------------\n" % (comm.replace("--", "\n    --"))
                        report['ready'].append(printbold)
                    else:
                        report['skipped'].append(printbold)

            elif run:
                report['not ready'].append(printbold)
                if options['run'] == "run":
                    r += "\n     ... ERROR: images missing, skipping this BOLD!"
                else:
                    r += "\n     ... ERROR: images missing, this BOLD would be skipped!"
            else:
                report['not ready'].append(printbold)
                if options['run'] == "run":
                    r += "\n     ... ERROR: No hcp info for session, skipping this BOLD!"
                else:
                    r += "\n     ... ERROR: No hcp info for session, this BOLD would be skipped!"

            # log beautify
            r += "\n\n"

        else:
            r += "\n===> ERROR: Hand reclassification failed for bold: %s!" % printbold
            report['failed'].append(printbold) 
            boldok = False

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = "\n\n\n --- Failed during processing of bold %s with error:\n" % (printbold)
        r += str(errormessage)
        report['failed'].append(printbold)
    except:
        r += "\n --- Failed during processing of bold %s with error:\n %s\n" % (printbold, traceback.format_exc())
        report['failed'].append(printbold)

    return {'r': r, 'report': report}


def executeHCPMultiReApplyFix(sinfo, options, overwrite, hcp, run, group):
    # get group data
    groupname = group["name"]
    bolds = group["bolds"]

    # prepare return variables
    r = ""
    report = {'done': [], 'incomplete': [], 'failed': [], 'ready': [], 'not ready': [], 'skipped': []}

    try:
        r += "\n----------------------------------------------------------------"
        r += "\n---> %s group %s" % (action("Processing", options['run']), groupname)
        groupok = True

        # --- check for bold images and prepare images parameter
        boldtargets = ""

        # check if files for all bolds exist
        for b in bolds:
            # boldok
            boldok = True

            # extract data
            _, _, _, boldinfo = b

            if 'filename' in boldinfo and options['hcp_filename'] == 'original':
                printbold  = boldinfo['filename']
                boldtarget = boldinfo['filename']
            else:
                printbold  = str(bold)
                boldtarget = "%s%s" % (options['hcp_bold_prefix'], printbold)

            boldimg = os.path.join(hcp['hcp_nonlin'], 'Results', boldtarget, "%s.nii.gz" % (boldtarget))
            r, boldok = checkForFile2(r, boldimg, '\n     ... bold image %s present' % boldtarget, '\n     ... ERROR: bold image [%s] missing!' % boldimg, status=boldok)

            if not boldok:
                groupok = False
                break
            else:
                # add @ separator
                if boldtargets is not "":
                    boldtargets = boldtargets + "@"

                # add latest image
                boldtargets = boldtargets + boldtarget

        # run HCP hand reclassification
        r += "\n---> Executing HCP Hand reclassification for group: %s\n" % groupname
        result = executeHCPHandReclassification(sinfo, options, overwrite, hcp, run, False, groupname, groupname)

        # merge r
        r += result['r']

        # check if hand reclassification was OK
        rcReport = result['report']
        if rcReport['incomplete'] == [] and rcReport['failed'] == [] and rcReport['not ready'] == []:
            groupok = True

            # matlab run mode, compiled=0, interpreted=1, octave=2
            matlabrunmode = 0
            if 'hcp_matlab_mode' in options:
                if options['hcp_matlab_mode'] == "compiled":
                    matlabrunmode = 0
                elif options['hcp_matlab_mode'] == "interpreted":
                    matlabrunmode = 1
                elif options['hcp_matlab_mode'] == "octave":
                    matlabrunmode = 2
                else:
                    r += "\n     ... ERROR: wrong value for the hcp_matlab_mode parameter!"
                    groupok = False

            # regname
            regname = "NONE"
            if 'hcp_regname' not in options or options['hcp_regname'] != "":
                regname = options['hcp_regname']

            # highpass and regname
            highpass = 0 if 'hcp_icafix_highpass' not in options else options['hcp_icafix_highpass']

            comm = '%(script)s \
                --path="%(path)s" \
                --subject="%(subject)s" \
                --fmri-names="%(boldtargets)s" \
                --concat-fmri-name="%(groupname)s" \
                --high-pass="%(highpass)d" \
                --reg-name="%(regname)s" \
                --low-res-mesh="%(lowresmesh)s" \
                --matlab-run-mode="%(matlabrunmode)d" \
                --motion-regression="%(motionregression)s" \
                --delete-intermediates="%(deleteintermediates)s"' % {
                    'script'              : os.path.join(hcp['hcp_base'], 'ICAFIX', 'ReApplyFixMultiRunPipeline.sh'),
                    'path'                : sinfo['hcp'],
                    'subject'             : sinfo['id'] + options['hcp_suffix'],
                    'boldtargets'         : boldtargets,
                    'groupname'           : groupname,
                    'highpass'            : highpass,
                    'regname'             : regname,
                    'lowresmesh'          : 32 if 'hcp_lowresmesh' not in options else options['hcp_lowresmesh'],
                    'matlabrunmode'       : matlabrunmode,
                    'motionregression'    : "FALSE" if 'hcp_icafix_domotionreg' not in options else options['hcp_icafix_domotionreg'],
                    'deleteintermediates' : "FALSE" if 'hcp_icafix_deleteintermediates' not in options else options['hcp_icafix_deleteintermediates']}

            # -- Test files
            # postfix
            postfix = "%s%s_hp%s_clean.dtseries.nii" % (groupname, options['hcp_cifti_tail'], highpass)
            if regname != "NONE" and regname != "":
                postfix = "%s%s_%s_hp%s_clean.dtseries.nii" % (groupname, options['hcp_cifti_tail'], regname, highpass)

            tfile = os.path.join(hcp['hcp_nonlin'], 'Results', groupname, postfix)
            fullTest = None

            # -- Run
            if run and groupok:
                if options['run'] == "run":
                    r, endlog, _, failed = runExternalForFile(tfile, comm, 'Running multi-run HCP ReApplyFix', overwrite=overwrite, thread=sinfo['id'], remove=options['log'] == 'remove', task=options['command_ran'], logfolder=options['comlogs'], logtags=[options['logtag'], groupname], fullTest=fullTest, shell=True, r=r)

                    if failed:
                        report['failed'].append(groupname)
                    else:
                        report['done'].append(groupname)

                # -- just checking
                else:
                    passed, _, r, failed = checkRun(tfile, fullTest, 'multi-run HCP ReApplyFix ' + groupname, r)
                    if passed is None:
                        r += "\n     ... multi-run HCP ReApplyFix can be run"
                        r += "\n-----------------------------------------------------\nCommand to run:\n %s\n-----------------------------------------------------\n" % (comm.replace("--", "\n    --"))
                        report['ready'].append(groupname)
                    else:
                        report['skipped'].append(groupname)

            elif run:
                report['not ready'].append(groupname)
                if options['run'] == "run":
                    r += "\n     ... ERROR: images missing, skipping this group!"
                else:
                    r += "\n     ... ERROR: images missing, this group would be skipped!"
            else:
                report['not ready'].append(groupname)
                if options['run'] == "run":
                    r += "\n     ... ERROR: No hcp info for session, skipping this group!"
                else:
                    r += "\n     ... ERROR: No hcp info for session, this group would be skipped!"

            # log beautify
            r += "\n\n"

        else:
            r += "\n===> ERROR: Hand reclassification failed for bold: %s!" % printbold
            groupok = False

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = "\n\n\n --- Failed during processing of group %s with error:\n" % (groupname)
        r += str(errormessage)
        report['failed'].append(groupname)
    except:
        r += "\n --- Failed during processing of group %s with error:\n %s\n" % (groupname, traceback.format_exc())
        report['failed'].append(groupname)

    return {'r': r, 'report': report}


def executeHCPHandReclassification(sinfo, options, overwrite, hcp, run, singleFix, boldtarget, printbold):
    # prepare return variables
    r = ""
    report = {'done': [], 'incomplete': [], 'failed': [], 'ready': [], 'not ready': [], 'skipped': []}

    try:
        r += "\n---> %s ICA %s" % (action("Processing", options['run']), printbold)
        boldok = True

        # load parameters or use default values
        if singleFix:
            highpass = 2000 if 'hcp_icafix_highpass' not in options else options['hcp_icafix_highpass']
        else:
            highpass = 0 if 'hcp_icafix_highpass' not in options else options['hcp_icafix_highpass']

        # --- check for bold image
        icaimg = os.path.join(hcp['hcp_nonlin'], 'Results', boldtarget, "%s_hp%s_clean.nii.gz" % (boldtarget, highpass))
        r, boldok = checkForFile2(r, icaimg, '\n     ... preprocessed ICA present', '\n     ... ERROR: preprocessed ICA missing!', status=boldok)

        comm = '%(script)s \
            --study-folder="%(studyfolder)s" \
            --subject="%(subject)s" \
            --fmri-name="%(boldtarget)s" \
            --high-pass="%(highpass)d"' % {
                'script'            : os.path.join(hcp['hcp_base'], 'ICAFIX', 'ApplyHandReClassifications.sh'),
                'studyfolder'       : sinfo['hcp'],
                'subject'           : sinfo['id'] + options['hcp_suffix'],
                'boldtarget'        : boldtarget,
                'highpass'          : highpass}

        # -- Test files
        tfile = os.path.join(hcp['hcp_nonlin'], 'Results', boldtarget, "%s_hp%s.ica" % (boldtarget, highpass), "HandNoise.txt")
        fullTest = None

        # -- Run
        if run and boldok:
            if options['run'] == "run":
                if overwrite and os.path.exists(tfile):
                    os.remove(tfile)

                r, endlog, _, failed = runExternalForFile(tfile, comm, 'Running HCP HandReclassification', overwrite=overwrite, thread=sinfo['id'], remove=options['log'] == 'remove', task="hcp_HandReclassification", logfolder=options['comlogs'], logtags=[options['logtag'], boldtarget], fullTest=fullTest, shell=True, r=r)

                if failed:
                    report['failed'].append(printbold)
                else:
                    report['done'].append(printbold)

            # -- just checking
            else:
                passed, _, r, failed = checkRun(tfile, fullTest, 'HCP HandReclassification ' + boldtarget, r)
                if passed is None:
                    r += "\n     ... HCP HandReclassification can be run"
                    r += "\n-----------------------------------------------------\nCommand to run:\n %s\n-----------------------------------------------------\n" % (comm.replace("--", "\n    --"))
                    report['ready'].append(printbold)
                else:
                    report['skipped'].append(printbold)

        elif run:
            report['not ready'].append(printbold)
            if options['run'] == "run":
                r += "\n     ... ERROR: images missing, skipping this BOLD!"
            else:
                r += "\n     ... ERROR: images missing, this BOLD would be skipped!"
        else:
            report['not ready'].append(printbold)
            if options['run'] == "run":
                r += "\n     ... ERROR: No hcp info for session, skipping this BOLD!"
            else:
                r += "\n     ... ERROR: No hcp info for session, this BOLD would be skipped!"

        # log beautify
        r += "\n"

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = "\n\n\n --- Failed during processing of bold %s with error:\n" % (printbold)
        r = str(errormessage)
        report['failed'].append(printbold)
    except:
        r += "\n --- Failed during processing of bold %s with error:\n %s\n" % (printbold, traceback.format_exc())
        report['failed'].append(printbold)

    return {'r': r, 'report': report}


def hcpDTIFit(sinfo, options, overwrite=False, thread=0):
    """
    hcpDTIFit - documentation not yet available.
    """

    r = "\n---------------------------------------------------------"
    r += "\nSession id: %s \n[started on %s]" % (sinfo['id'], datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))
    r += "\n%s HCP DTI Fix ..." % (action("Running", options['run']))

    run    = True
    report = "Error"

    try:
        doOptionsCheck(options, sinfo, 'hcp_PreFS')
        doHCPOptionsCheck(options, sinfo, 'hcp_PreFS')
        hcp = getHCPPaths(sinfo, options)

        if 'hcp' not in sinfo:
            r += "---> ERROR: There is no hcp info for session %s in batch.txt" % (sinfo['id'])
            run = False

        for tfile in ['bvals', 'bvecs', 'data.nii.gz', 'nodif_brain_mask.nii.gz']:
            if not os.path.exists(os.path.join(hcp['T1w_folder'], 'Diffusion', tfile)):
                r += "---> ERROR: Could not find %s file!" % (tfile)
                run = False
            else:
                r += "---> %s found!" % (tfile)

        comm = 'dtifit \
            --data="%(data)s" \
            --out="%(out)s" \
            --mask="%(mask)s" \
            --bvecs="%(bvecs)s" \
            --bvals="%(bvals)s"' % {
                'data'              : os.path.join(hcp['T1w_folder'], 'Diffusion', 'data'),
                'out'               : os.path.join(hcp['T1w_folder'], 'Diffusion', 'dti'),
                'mask'              : os.path.join(hcp['T1w_folder'], 'Diffusion', 'nodif_brain_mask'),
                'bvecs'             : os.path.join(hcp['T1w_folder'], 'Diffusion', 'bvecs'),
                'bvals'             : os.path.join(hcp['T1w_folder'], 'Diffusion', 'bvals')}

        # -- Test files
        
        tfile = os.path.join(hcp['T1w_folder'], 'Diffusion', 'dti_FA.nii.gz')

        # -- Run

        if run:
            
            if options['run'] == "run":
                if overwrite and os.path.exists(tfile):
                    os.remove(tfile)

                r, endlog, report, failed = runExternalForFile(tfile, comm, 'Running HCP DTI Fit', overwrite=overwrite, thread=sinfo['id'], remove=options['log'] == 'remove', task=options['command_ran'], logfolder=options['comlogs'], logtags=options['logtag'], shell=True, r=r)


            # -- just checking
            else:
                passed, report, r, failed = checkRun(tfile, fullTest, 'HCP DTI Fit', r)
                if passed is None:
                    r += "\n---> HCP DTI Fit can be run"
                    report = "HCP DTI Fit FS can be run"
                    failed = 0

        else:
            r += "---> Session can not be processed."
            report = "HCP DTI Fit can not be run"
            failed = 1

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = str(errormessage)
        failed = 1
    except:
        r += "\nERROR: Unknown error occured: \n...................................\n%s...................................\n" % (traceback.format_exc())
        failed = 1

    r += "\n\nHCP Diffusion Preprocessing %s on %s\n---------------------------------------------------------" % (action("completed", options['run']), datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))

    # print r
    return (r, (sinfo['id'], report, failed))


def hcpBedpostx(sinfo, options, overwrite=False, thread=0):
    """
    hcpBedpostx - documentation not yet available.
    """

    r = "\n---------------------------------------------------------"
    r += "\nSession id: %s \n[started on %s]" % (sinfo['id'], datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))
    r += "\n%s HCP Bedpostx GPU ..." % (action("Running", options['run']))

    run    = True
    report = "Error"

    try:
        doOptionsCheck(options, sinfo, 'hcp_PreFS')
        doHCPOptionsCheck(options, sinfo, 'hcp_PreFS')
        hcp = getHCPPaths(sinfo, options)

        if 'hcp' not in sinfo:
            r += "---> ERROR: There is no hcp info for session %s in batch.txt" % (sinfo['id'])
            run = False

        for tfile in ['bvals', 'bvecs', 'data.nii.gz', 'nodif_brain_mask.nii.gz']:
            if not os.path.exists(os.path.join(hcp['T1w_folder'], 'Diffusion', tfile)):
                r += "---> ERROR: Could not find %s file!" % (tfile)
                run = False

        for tfile in ['FA', 'L1', 'L2', 'L3', 'MD', 'MO', 'S0', 'V1', 'V2', 'V3']:
            if not os.path.exists(os.path.join(hcp['T1w_folder'], 'Diffusion', 'dti_' + tfile + '.nii.gz')):
                r += "---> ERROR: Could not find %s file!" % (tfile)
                run = False
        if not run:
            r += "---> all necessary files found!"

        comm = 'fslbedpostx_gpu \
            %(data)s \
            --nf=%(nf)s \
            --rician \
            --model="%(model)s"' % {
                'data'              : os.path.join(hcp['T1w_folder'], 'Diffusion', '.'),
                'nf'                : "3",
                'model'             : "2"}

        # -- test files

        tfile = os.path.join(hcp['T1w_folder'], 'Diffusion.bedpostX', 'mean_fsumsamples.nii.gz')

        # -- run

        if run:
            if options['run'] == "run":
                if overwrite and os.path.exists(tfile):
                    os.remove(tfile)

                r, endlog, report, failed = runExternalForFile(tfile, comm, 'Running HCP BedpostX', overwrite=overwrite, thread=sinfo['id'], remove=options['log'] == 'remove', task=options['command_ran'], logfolder=options['comlogs'], logtags=options['logtag'], shell=True, r=r)

            # -- just checking
            else:
                passed, report, r, failed = checkRun(tfile, fullTest, 'HCP BedpostX', r)
                if passed is None:
                    r += "\n---> HCP BedpostX can be run"
                    report = "HCP BedpostX can be run"
                    failed = 0

        else:
            r += "---> Session can not be processed."
            report = "HCP BedpostX can not be run"
            failed = 1

    except (ExternalFailed, NoSourceFolder), errormessage:
        r = str(errormessage)
        failed = 1
    except:
        r += "\nERROR: Unknown error occured: \n...................................\n%s...................................\n" % (traceback.format_exc())
        failed = 1

    r += "\n\nHCP Diffusion Preprocessing %s on %s\n---------------------------------------------------------" % (action("completed", options['run']), datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))

    print r
    return (r, (sinfo['id'], report, failed))


def mapHCPData(sinfo, options, overwrite=False, thread=0):
    """
    mapHCPData [... processing options]

    USE
    ===

    mapHCPData maps the results of the HCP preprocessing (in MNINonLinear) to
    the <subjectsfolder>/<session id>/images folder structure. Specifically, it
    copies the files and folders:

    * T1w.nii.gz                  -> images/structural/T1w.nii.gz
    * aparc+aseg.nii.gz           -> images/segmentation/freesurfer/mri/aparc+aseg_t1.nii.gz
                                  -> images/segmentation/freesurfer/mri/aparc+aseg_bold.nii.gz
                                     (2mm iso downsampled version)
    * fsaverage_LR32k/*           -> images/segmentation/hcp/fsaverage_LR32k
    * BOLD_[N].nii.gz             -> images/functional/[boldname][N].nii.gz
    * BOLD_[N][tail].dtseries.nii -> images/functional/[boldname][N][hcp_cifti_tail].dtseries.nii
    * Movement_Regressors.txt     -> images/functional/movement/[boldname][N]_mov.dat

    PARAMETERS
    ==========

    The relevant processing parameters are:

    --sessions         ... The batch.txt file with all the session information
                           [batch.txt].
    --subjectsfolder   ... The path to the study/subjects folder, where the
                           imaging data is supposed to go [.].
    --cores            ... How many cores to utilize [1].
    --overwrite        ... Whether to overwrite existing data (yes) or not (no)
                           [no].
    --hcp_cifti_tail   ... The tail (see above) that specifies, which version of
                           the cifti files to copy over [].
    --bolds            ... Which bold images (as they are specified in the
                           batch.txt file) to copy over. It can be a single
                           type (e.g. 'task'), a pipe separated list (e.g.
                           'WM|Control|rest') or 'all' to copy all [all].
    --boldname         ... The prefix for the fMRI files in the images folder
                           [bold].
    --hcp_bold_variant ... Optional variant of HCP BOLD preprocessing. If
                           specified, the results will be copied/linked from
                           `Results.<hcp_bold_variant>` into 
                           `images/functional.<hcp_bold_variant>. []

    The parameters can be specified in command call or subject.txt file.
    If possible, the files are not copied but rather hard links are created to
    save space. If hard links can not be created, the files are copied.

    Specific attention needs to be paid to the `hcp_cifti_tail` parameter. Using
    the regular HCP minimal preprocessing pipelines, CIFTI files have a tail 
    `_Atlas` e.g. `BOLD_6_Atlas.dtseries.nii`. This tail might be changed if 
    another method was used for surface registration or if CIFTI images were 
    additionally processed after the HCP minimal processing pipeline. `boldname` 
    and `hcp_cifti_tail` define the final name of the fMRI images linked into the 
    `images/functional` folder. Specifically, with `boldname=bold` and 
    `hcp_cifti_tail=_Atlas`, volume files will be named using formula: 
    `<boldname>[N].nii.gz` (e.g. `bold1.nii.gz`), and cifti files will be named 
    using formula: `<boldname>[N]<hcp_cifti_tail>.dtseries.nii` (e.g. 
    `bold1_Atlas.dtseries.nii`).


    EXAMPLE USE
    ===========
    
    ```
    qunex mapHCPData sessions=fcMRI/subjects.hcp.txt subjectsfolder=subjects \\
          overwrite=no hcp_cifti_tail=_Atlas bolds=all
    ```
    
    ----------
    Written by Grega Repovš

    Changelog
    2016-12-24 - Grega Repovš - Added documentation, fixed copy of volume images.
    2017-03-25 - Grega Repovš - Added more detailed reporting of progress.
    2018-07-17 - Grega Repovš - Added hcp_bold_variant option.
    2019-04-25 - Grega Repovš - Changed subjects to sessions
    2019-05-26 - Grega Repovš - Added support for boldnamekey
    2020-01-14 - Grega Repovš - Expanded documentation on use of boldname and hcp_cifti_tail
    """

    
    r = "\n---------------------------------------------------------"
    r += "\nSession id: %s \n[started on %s]" % (sinfo['id'], datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))
    r += "\nMapping HCP data ... \n"
    r += "\n   The command will map the results of the HCP preprocessing from sessions's hcp\n   to sessions's images folder. It will map the T1 structural image, aparc+aseg \n   segmentation in both high resolution as well as one downsampled to the \n   resolution of BOLD images. It will map the 32k surface mapping data, BOLD \n   data in volume and cifti representation, and movement correction parameters. \n\n   Please note: when mapping the BOLD data, two parameters are key: \n\n   --bolds parameter defines which BOLD files are mapped based on their\n     specification in batch.txt file. Please see documentation for formatting. \n        If the parameter is not specified the default value is 'all' and all BOLD\n        files will be mapped. \n\n   --hcp_cifti_tail specifies which kind of the cifti files will be copied over. \n     The tail is added after the boldname[N] start. If the parameter is not specified \n     explicitly the default is ''.\n\n   Based on settings:\n\n    * %s BOLD files will be copied\n    * '%s' cifti tail will be used." % (", ".join(options['bolds'].split("|")), options['hcp_cifti_tail'])
    if options['hcp_bold_variant']:
        r += "\n   As --hcp_bold_variant was set to '%s', the files will be copied/linked to 'images/functional.%s!" % (options['hcp_bold_variant'], options['hcp_bold_variant'])
    r += "\n\n........................................................"

    # --- file/dir structure


    f = getFileNames(sinfo, options)
    d = getSubjectFolders(sinfo, options)

    #    MNINonLinear/Results/<boldname>/<boldname>.nii.gz -- volume
    #    MNINonLinear/Results/<boldname>/<boldname>_Atlas.dtseries.nii -- cifti
    #    MNINonLinear/Results/<boldname>/Movement_Regressors.txt -- movement
    #    MNINonLinear/T1w.nii.gz -- atlas T1 hires
    #    MNINonLinear/aparc+aseg.nii.gz -- FS hires segmentation

    # ------------------------------------------------------------------------------------------------------------
    #                                                                                      map T1 and segmentation

    report = {}
    failed = 0

    r += "\n\nSource folder: " + d['hcp']
    r += "\nTarget folder: " + d['s_images']

    r += "\n\nStructural data: ..."
    status = True

    if os.path.exists(f['t1']) and not overwrite:
        r += "\n ... T1 ready"
        report['T1'] = 'present'
    else:
        status, r = linkOrCopy(os.path.join(d['hcp'], 'MNINonLinear', 'T1w.nii.gz'), f['t1'], r, status, "T1")
        report['T1'] = 'copied'

    if os.path.exists(f['fs_aparc_t1']) and not overwrite:
        r += "\n ... highres aseg+aparc ready"
        report['hires aseg+aparc'] = 'present'
    else:
        status, r = linkOrCopy(os.path.join(d['hcp'], 'MNINonLinear', 'aparc+aseg.nii.gz'), f['fs_aparc_t1'], r, status, "highres aseg+aparc")
        report['hires aseg+aparc'] = 'copied'

    if os.path.exists(f['fs_aparc_bold']) and not overwrite:
        r += "\n ... lowres aseg+aparc ready"
        report['lores aseg+aparc'] = 'present'
    else:
        if os.path.exists(f['fs_aparc_bold']):
            os.remove(f['fs_aparc_bold'])
        if os.path.exists(os.path.join(d['hcp'], 'MNINonLinear', 'T1w_restore.2.nii.gz')) and os.path.exists(f['fs_aparc_t1']):
            _, endlog, _, failedcom = runExternalForFile(f['fs_aparc_bold'], 'flirt -interp nearestneighbour -ref %s -in %s -out %s -applyisoxfm 2' % (os.path.join(d['hcp'], 'MNINonLinear', 'T1w_restore.2.nii.gz'), f['fs_aparc_t1'], f['fs_aparc_bold']), ' ... resampling t1 cortical segmentation (%s) to bold space (%s)' % (os.path.basename(f['fs_aparc_t1']), os.path.basename(f['fs_aparc_bold'])), overwrite=overwrite, logfolder=options['comlogs'], logtags=options['logtag'], shell=True)
            if failedcom:
                report['lores aseg+aparc'] = 'failed'
                failed += 1
            else:
                report['lores aseg+aparc'] = 'generated'
        else:
            r += "\n ... ERROR: could not generate downsampled aseg+aparc, files missing!"
            report['lores aseg+aparc'] = 'failed'
            status = False
            failed += 1

    report['surface'] = 'ok'
    if os.path.exists(os.path.join(d['hcp'], 'MNINonLinear', 'fsaverage_LR32k')):
        r += "\n ... processing surface files"
        sfiles = glob.glob(os.path.join(d['hcp'], 'MNINonLinear', 'fsaverage_LR32k', '*.*'))
        npre, ncp = 0, 0
        if len(sfiles):
            sid = os.path.basename(sfiles[0]).split(".")[0]
        for sfile in sfiles:
            tfile = os.path.join(d['s_s32k'], ".".join(os.path.basename(sfile).split(".")[1:]))
            if os.path.exists(tfile) and not overwrite:
                npre += 1
            else:
                if ".spec" in tfile:
                    s = file(sfile).read()
                    s = s.replace(sid + ".", "")
                    tf = open(tfile, 'w')
                    print >> tf, s
                    tf.close()
                    r += "\n     -> updated .spec file [%s]" % (sid)
                    ncp += 1
                    continue
                if linkOrCopy(sfile, tfile):
                    ncp += 1
                else:
                    r += "\n     -> ERROR: could not map or copy %s" % (sfile)
                    report['surface'] = 'error'
                    failed += 1
        if npre:
            r += "\n     -> %d files already copied" % (npre)
        if ncp:
            r += "\n     -> copied %d surface files" % (ncp)
    else:
        r += "\n ... ERROR: missing folder: %s!" % (os.path.join(d['hcp'], 'MNINonLinear', 'fsaverage_LR32k'))
        status = False
        report['surface'] = 'error'
        failed += 1

    # ------------------------------------------------------------------------------------------------------------
    #                                                                                          map functional data

    r += "\n\nFunctional data: \n ... mapping %s BOLD files\n ... using '%s' cifti tail\n" % (", ".join(options['bolds'].split("|")), options['hcp_cifti_tail'])

    report['boldok'] = 0
    report['boldfail'] = 0
    report['boldskipped'] = 0

    if options['hcp_bold_variant'] == "":
        bvar = ''
    else:
        bvar = '.' + options['hcp_bold_variant']    

    bolds, skipped, report['boldskipped'], r = useOrSkipBOLD(sinfo, options, r)

    for boldnum, boldname, boldtask, boldinfo in bolds:

        r += "\n ... " + boldname

        # --- filenames
        options['image_target'] = 'nifti'        # -- needs to be set to correctly copy volume files
        f.update(getBOLDFileNames(sinfo, boldname, options))

        status = True
        bname  = ""

        try:            
            # -- get source bold name

            if 'filename' in boldinfo and options['hcp_filename'] == 'original':
                bname = boldinfo['filename']
            elif 'bold' in boldinfo:
                bname = boldinfo['bold']
            else:
                bname = "%s%d" % (options['hcp_bold_prefix'], boldnum)

            # -- check if present and map

            boldpath = os.path.join(d['hcp'], 'MNINonLinear', 'Results', bname)

            if not os.path.exists(boldpath):
                r += "\n     ... ERROR: source folder does not exist [%s]!" % (boldpath)
                status = False

            else:   
                if os.path.exists(f['bold_vol']) and not overwrite:
                    r += "\n     ... volume image ready"
                else:
                    # r += "\n     ... linking volume image \n         %s to\n         -> %s" % (os.path.join(boldpath, bname + '.nii.gz'), f['bold'])
                    status, r = linkOrCopy(os.path.join(boldpath, bname + '.nii.gz'), f['bold'], r, status, "volume image", "\n     ... ")

                if os.path.exists(f['bold_dts']) and not overwrite:
                    r += "\n     ... grayordinate image ready"
                else:
                    # r += "\n     ... linking cifti image\n         %s to\n         -> %s" % (os.path.join(boldpath, bname + options['hcp_cifti_tail'] + '.dtseries.nii'), f['bold_dts'])
                    status, r = linkOrCopy(os.path.join(boldpath, bname + options['hcp_cifti_tail'] + '.dtseries.nii'), f['bold_dts'], r, status, "grayordinate image", "\n     ... ")

                if os.path.exists(f['bold_mov']) and not overwrite:
                    r += "\n     ... movement data ready"
                else:
                    if os.path.exists(os.path.join(boldpath, 'Movement_Regressors.txt')):
                        mdata = [line.strip().split() for line in open(os.path.join(boldpath, 'Movement_Regressors.txt'))]
                        mfile = open(f['bold_mov'], 'w')
                        print >> mfile, "#frame     dx(mm)     dy(mm)     dz(mm)     X(deg)     Y(deg)     Z(deg)"
                        c = 0
                        for mline in mdata:
                            c += 1
                            mline = "%6d   %s" % (c, "   ".join(mline[0:6]))
                            print >> mfile, mline.replace(' -', '-')
                        mfile.close()
                        r += "\n     ... movement data prepared"
                    else:
                        r += "\n     ... ERROR: could not prepare movement data, source does not exist: %s" % os.path.join(boldpath, 'Movement_Regressors.txt')
                        failed += 1
                        status = False

            if status:
                r += "\n     ---> Data ready!\n"
                report['boldok'] += 1
            else:
                r += "\n     ---> ERROR: Data missing, please check source!\n"
                report['boldfail'] += 1
                failed += 1

        except (ExternalFailed, NoSourceFolder), errormessage:
            r = str(errormessage)
            report['boldfail'] += 1
            failed += 1
        except:
            r += "\nERROR: Unknown error occured: \n...................................\n%s...................................\n" % (traceback.format_exc())
            time.sleep(3)
            failed += 1

    if len(skipped) > 0:
        r += "\nThe following BOLD images were not mapped as they were not specified in\n'--bolds=\"%s\"':\n" % (options['bolds'])
        for boldnum, boldname, boldtask, boldinfo in skipped:
            if 'filename' in boldinfo and options['hcp_filename'] == 'original':
                r += "\n ... %s [task: '%s']" % (boldinfo['filename'], boldtask)
            else:
                r += "\n ... %s [task: '%s']" % (boldname, boldtask)

    r += "\n\nHCP data mapping completed on %s\n---------------------------------------------------------------- \n" % (datetime.now().strftime("%A, %d. %B %Y %H:%M:%S"))
    rstatus = "T1: %(T1)s, aseg+aparc hires: %(hires aseg+aparc)s lores: %(lores aseg+aparc)s, surface: %(surface)s, bolds ok: %(boldok)d, bolds failed: %(boldfail)d, bolds skipped: %(boldskipped)d" % (report)

    # print r
    return (r, (sinfo['id'], rstatus, failed))
