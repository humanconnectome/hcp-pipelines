#!/usr/bin/env python3

"""
Abstract Base Class for One Subject Completion Checker Classes
"""

# import of built-in modules
import os
import sys

# import of third-party modules

# import of local modules
import ccf.one_subject_completion_checker as one_subject_completion_checker

# authorship information
__author__ = "Timothy B. Brown"
__copyright__ = "Copyright 2019, Connectome Coordination Facility"
__maintainer__ = "Junil Chang"

class OneSubjectCompletionXnatChecker(one_subject_completion_checker.OneSubjectCompletionChecker):
	"""
	Abstract base class for classes that are used to check the completion
	of pipeline processing for one subject
	"""

	def my_prerequisite_dir_full_paths(self, archive, subject_info):
		pass

	def my_resource_time_stamp(self, archive, subject_info):
		return os.path.getmtime(self.my_resource(archive, subject_info))
		
	def does_processed_resource_exist(self, archive, subject_info):
		fullpath = self.my_resource(archive,subject_info)
		return os.path.isdir(fullpath)	

	def latest_prereq_resource_time_stamp(self, archive, subject_info):
		latest_time_stamp = 0
		prerequisite_dir_paths = self.my_prerequisite_dir_full_paths(archive, subject_info)

		for full_path in prerequisite_dir_paths:
			this_time_stamp = os.path.getmtime(full_path)
			if this_time_stamp > latest_time_stamp:
				latest_time_stamp = this_time_stamp

		return latest_time_stamp

	def is_processing_marked_complete(self, archive, subject_info):

		# If the processed resource does not exist, then the process is certainly not marked
		# as complete. The file that marks completeness would be in that resource.
		if not self.does_processed_resource_exist(archive, subject_info):
			return False

		resource_path = self.my_resource(archive,subject_info) + os.sep + subject_info.subject_id + '_' + subject_info.classifier + os.sep +'ProcessingInfo'
		
		subject_pipeline_name = subject_info.subject_id + '_' + subject_info.classifier
		subject_pipeline_name_check = subject_info.subject_id + '.' + subject_info.classifier
		if (subject_info.extra.lower() != 'all' and subject_info.extra !=''):
			subject_pipeline_name += '_' + subject_info.extra
			subject_pipeline_name_check += '.' + subject_info.extra
		subject_pipeline_name += '.' + self.PIPELINE_NAME
		subject_pipeline_name_check += '.' + self.PIPELINE_NAME
		
		completion_marker_file_path = resource_path + os.sep + subject_pipeline_name_check + '.XNAT_CHECK.success'
		starttime_marker_file_path = resource_path + os.sep + subject_pipeline_name + '.starttime'
		
		# If the completion marker file does not exist, the the processing is certainly not marked
		# as complete.
		marker_file_exists = os.path.exists(completion_marker_file_path)
		if not marker_file_exists:
			return False

		# If the completion marker file is older than the starttime marker file, then any mark
		# of completeness is invalid.
		if not os.path.exists(starttime_marker_file_path):
			return False

		if os.path.getmtime(completion_marker_file_path) < os.path.getmtime(starttime_marker_file_path):
			return False

		# If the completion marker file does exist, then look at the contents for further
		# confirmation.

		f = open(completion_marker_file_path, "r")
		lines = f.readlines()

		if lines[-1].strip() != 'Completion Check was successful':
			return False

		return True
		
	def is_processing_complete(self, archive, fieldmap, subject_info,
							   verbose=False, output=sys.stdout, short_circuit=True):
		# If the processed resource does not exist, then the processing is certainly not complete.
		if not self.does_processed_resource_exist(archive, subject_info):
			if verbose:
				print("resource: " + self.my_resource(archive, subject_info) + " DOES NOT EXIST",
					  file=output)
			return False

		# If processed resource is not newer than prerequisite resources, then the processing
		# is not complete.
		resource_time_stamp = self.my_resource_time_stamp(archive, subject_info)
		latest_prereq_time_stamp = self.latest_prereq_resource_time_stamp(archive, subject_info)
		
		if resource_time_stamp <= latest_prereq_time_stamp:
			if verbose:
				print("resource: " + self.my_resource(archive, subject_info) + " IS NOT NEWER THAN ALL PREREQUISITES", file=output)
			return False

		resource_file_path=self.my_resource(archive, subject_info)
		# If processed resource exists and is newer than all the prerequisite resources, then check
		# to see if all the expected files exist
		expected_file_list = self.list_of_expected_files(resource_file_path, fieldmap, subject_info)
		return self.do_all_files_exist(expected_file_list, verbose, output, short_circuit)
