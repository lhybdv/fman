from build_impl import copy_python_library, upload_to_s3
from fbs import path, SETTINGS
from fbs.cmdline import command
from fbs.freeze.windows import freeze_windows
from os import remove
from os.path import join, dirname
from shutil import copy, rmtree

@command
def freeze():
	_patch_fbs_missing_dlls()
	freeze_windows()
	_copy_winpty_files()
	rmtree(path('${core_plugin_in_freeze_dir}/bin/mac'))
	rmtree(path('${core_plugin_in_freeze_dir}/bin/linux'))
	# Open Sans is only used on Linux. Further, it fails to load on some users'
	# Windows systems (see fman issue #480). Remove it to avoid problems,
	# improve startup performance and decrease fman's download size.
	# (Also note that a more elegant solution would be to only place
	# Open Sans.ttf in src/main/resources/*linux*/Plugins/Core. But the current
	# implementation cannot handle multiple dirs .../resources/main,
	# .../resources/linux for one plugin.)
	remove(path('${core_plugin_in_freeze_dir}/Open Sans.ttf'))
	copy_python_library('send2trash', path('${core_plugin_in_freeze_dir}'))

def _patch_fbs_missing_dlls():
	# fbs 1.2.7's freeze step insists on finding msvcr100/msvcr110/msvcp110 etc.
	# on PATH and aborts if any is missing. Those are the VC++ 2010/2012 runtimes,
	# which modern Windows installations no longer ship. Python 3.x only needs the
	# 140 series. So replace the check with a tolerant version: copy whatever is
	# available, silently skip the rest.
	import fbs.freeze.windows as fbs_windows
	fbs_windows._add_missing_dlls = _add_available_dlls

def _add_available_dlls():
	import fbs.freeze.windows as fbs_windows
	for dll_name in (
		'msvcr100.dll', 'msvcr110.dll', 'msvcp110.dll', 'vcruntime140.dll',
		'msvcp140.dll', 'concrt140.dll', 'vccorlib140.dll',
		'api-ms-win-crt-multibyte-l1-1-0.dll'
	):
		try:
			fbs_windows._add_missing_dll(dll_name)
		except LookupError:
			pass

def _copy_winpty_files():
	# winpty is only needed for password-protected archives (see
	# Core's zip.py). It is not available in every Python environment,
	# so do not abort the whole freeze when it is missing:
	try:
		import winpty
		winpty_dir = dirname(winpty.__file__)
		copy(join(winpty_dir, 'winpty-agent.exe'), path('${freeze_dir}'))
	except (ImportError, OSError) as e:
		print('Warning: Could not copy winpty-agent.exe: %s' % e)

@command
def upload():
	if SETTINGS['release']:
		src_path = path('target/fmanSetup.exe')
		dest_path = SETTINGS['version'] + '/fmanSetup.exe'
		upload_to_s3(src_path, dest_path)
		print('\nDone. Please upload fmanSetup.exe to update.fman.io now.')