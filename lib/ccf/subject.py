#!/usr/bin/env python3

"""
ccf/subject.py: Maintain information about a CCF subject.
"""

# import of built-in modules
import logging
import os

# import of third-party modules

# import of local modules
import utils.str_utils as str_utils

# authorship information
__author__ = "Timothy B. Brown"
__copyright__ = "Copyright 2017, Connectome Cordination Facility"
__maintainer__ = "Timothy B. Brown"

# create a module logger
module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.WARNING)


class SubjectInfo:
	"""
	This class maintains information about a CCF subject.
	"""

	@classmethod
	def DEFAULT_SEPARATOR(cls):
		return ":"

	def __init__(self, project=None, subject_id=None, classifier=None, extra=None):
		"""
		Initialize a SubjectInfo object.
		"""
		self._project = project
		self._subject_id = subject_id
		self._classifier = classifier
		self._extra = extra

	@property
	def project(self):
		"""
		Primary project
		"""
		return self._project

	@property
	def subject_id(self):
		"""
		Subject ID
		"""
		return self._subject_id

	@property
	def classifier(self):
		"""
		An additional piece of information used to classify the session. Sometimes (e.g. in HCP)
		this is the conventional specification of the TESLA rating of the MRI scanner
		used for collecting data in this archive (e.g. '3T' or '7T'). It might also be used
		to simply indicate that the session was for MRI scans (e.g. 'MR') or might be a visit
		indicator (e.g. 'V1', 'V2', 'V3', etc.).
		"""
		return self._classifier

	@property
	def extra(self):
		"""
		Extra processing information
		"""
		return self._extra

	def __str__(self):
		"""
		Returns informal string representation
		"""
		separator = SubjectInfo.DEFAULT_SEPARATOR()
		# return str(self.project) + separator + str(self.subject_id) + separator + str(self.classifier) + separator + str(self.extra)
		return separator.join([self.project, self.subject_id, self.classifier, self.extra])


def read_subject_info_list(file_name, separator=SubjectInfo.DEFAULT_SEPARATOR()):
	"""
	Reads a subject information list from the specified file.
	"""
	subject_info_list = []

	input_file = open(file_name, 'r')
	for line in input_file:
		# remove new line characters
		line = str_utils.remove_ending_new_lines(line)

		# remove leading and trailing spaces
		line = line.strip()

		# ignore blank lines and comment lines - starting with #
		if line != '' and line[0] != '#':
			(project, subject_id, classifier, extra) = line.split(separator)
			# Make the string 'None' in the file translate to a None type instead of
			# just the string itself
			if extra == 'None':
				extra = None
			subject_info = SubjectInfo(project, subject_id, classifier, extra)
			subject_info_list.append(subject_info)

	input_file.close()

	return subject_info_list


def write_subject_info_list(file_name, subject_info_list):
	"""
	Writes a subject list into the specified file.

	The file is overwritten, not appended to.
	"""
	output_file = open(file_name, 'w')

	for subject_info in subject_info_list:
		output_file.write(str(subject_info) + os.linesep)

	output_file.close()


def _simple_interactive_demo():

	print("-- Creating 2 CCF SubjectInfo objects --")
	subject_info1 = SubjectInfo('HCP_500', '100206', '3T', 'extra stuff')
	subject_info2 = SubjectInfo('HCP_1200', '100307', '3T')
	subject_info3 = SubjectInfo('testproject', 'HCA6018857', 'MR', 'extra stuff')

	print("-- Showing the CCF SubjectInfo objects --")
	print(str(subject_info1))
	print(str(subject_info2))
	print(str(subject_info3))

	test_file_name = 'test_subjects.txt'
	print("-- Writing the SubjectInfo objects to a text file: " + test_file_name + " --")
	subject_info_list_out = []
	subject_info_list_out.append(subject_info1)
	subject_info_list_out.append(subject_info2)
	subject_info_list_out.append(subject_info3)
	write_subject_info_list(test_file_name, subject_info_list_out)

	print("-- Retrieving the list of SubjectInfo objects from the file --")
	subject_info_list_in = read_subject_info_list(test_file_name)

	print("-- Showing the list of retrieved SubjectInfo objects --")
	for subject_info in subject_info_list_in:
		print(str(subject_info))

	print("-- Removing the text file --")
	os.remove(test_file_name)

if __name__ == '__main__':
	_simple_interactive_demo()
