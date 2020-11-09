#!/usr/bin/env python3

"""
Abstract Base Class for One Subject Completion Checker Classes
"""

# import of built-in modules
import abc
import os
import sys

# import of third-party modules

# import of local modules
import utils.file_utils as file_utils
import utils.os_utils as os_utils

# authorship information
__author__ = "Timothy B. Brown"
__copyright__ = "Copyright 2017, Connectome Coordination Facility"
__maintainer__ = "Timothy B. Brown"

class OneSubjectCompletionChecker(abc.ABC):
	"""
	Abstract base class for classes that are used to check the completion
	of pipeline processing for one subject
	"""

	@property
	def processing_name(self):
		"""Name of processing type to check (e.g. StructuralPreprocessing, FunctionalPreprocessing, etc.)"""
		raise NotImplementedError

	def expected_output_files_template_filename(self, fieldmap):
		"""Name of the file containing a list of templates for expected output files"""	
		return 'ExpectedOutputFiles-FieldMap-' + fieldmap + '.CCF.txt'
	
	def list_of_expected_files(self, working_dir, fieldmap, subject_info):

		hcp_run_utils = os_utils.getenv_required('HCP_RUN_UTILS')
		if os.path.isfile(hcp_run_utils + os.sep + self.processing_name + os.sep
				 + self.expected_output_files_template_filename(fieldmap)):
			f = open(hcp_run_utils + os.sep + self.processing_name + os.sep
					 + self.expected_output_files_template_filename(fieldmap))
		else:
			xnat_pbs_jobs = os_utils.getenv_required('XNAT_PBS_JOBS')
			f = open(xnat_pbs_jobs + os.sep + self.processing_name + os.sep
					 + self.expected_output_files_template_filename(fieldmap))
			
		root_dir = os.sep.join([working_dir, subject_info.subject_id + '_' + subject_info.classifier])
		l = file_utils.build_filename_list_from_file(f, root_dir,
													 subjectid=subject_info.subject_id + '_' + subject_info.classifier,
													 scan=subject_info.extra)
		return l
	
	def do_all_files_exist(self, file_name_list, verbose=False, output=sys.stdout, short_circuit=True):
		return file_utils.do_all_files_exist(file_name_list, verbose, output, short_circuit)
	
	def is_processing_complete(self, working_dir, fieldmap, subject_info,
							   verbose=False, output=sys.stdout, short_circuit=True):
		expected_file_list = self.list_of_expected_files(working_dir, fieldmap, subject_info)
		return self.do_all_files_exist(expected_file_list, verbose, output, short_circuit)
