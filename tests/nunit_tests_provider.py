# pylint: disable=C0301,C0103,C0111
from __future__ import print_function
from sys import platform
import os
import subprocess
import nunit_results_merger

this_path = os.path.abspath(os.path.dirname(__file__))

def install_cli_arguments(parser):
    parser.add_argument("--properties-file", action="store", help="Location of properties file.")
    parser.add_argument("--skip-building", action="store_true", help="Do not build tests before run.")

class NUnitTestSuite(object):
    nunit_path = os.path.join(this_path, './../lib/resources/tools/nunit3/nunit3-console.exe')
    output_files = []
    instances_count = 0

    def __init__(self, path):
        #super(NUnitTestSuite, self).__init__(path)
        self.path = path
    
    def check(self, options, number_of_runs): #API requires this method 
        pass 

    def prepare(self, options):
        NUnitTestSuite.instances_count += 1

        if not options.skip_building:
            print("Building {0}".format(self.path))
            if platform == "win32":
                builder = 'MSBuild.exe'
            else:
                builder = 'xbuild'
            result = subprocess.call([builder, '/p:PropertiesLocation={0}'.format(options.properties_file), '/p:OutputPath={0}'.format(options.results_directory), '/nologo', '/verbosity:quiet', '/p:OutputDir=tests_output', '/p:Configuration={0}'.format(options.configuration), self.path])
            if result != 0:
                print("Building project `{}` failed with error code: {}".format(self.path, result))
                return result
        else:
            print('Skipping the build')

        self.project_file = os.path.split(self.path)[1]
        self.output_file = os.path.join(options.results_directory, 'results-{}.xml'.format(self.project_file))
        NUnitTestSuite.output_files.append(self.output_file)

        return 0

    def run(self, options, run_id):
        print('Running ' + self.path)

        args = [NUnitTestSuite.nunit_path, '--domain=None', '--noheader', '--labels=Before', '--result={}'.format(self.output_file), self.project_file.replace("csproj", "dll")]
        if options.stop_on_error:
            args.append('--stoponerror')
        if platform.startswith("linux") or platform == "darwin":
            args.insert(0, 'mono')
            if options.port is not None:
                if options.suspend:
                    print('Waiting for a debugger at port: {}'.format(options.port))
                args.insert(1, '--debug')
                args.insert(2, '--debugger-agent=transport=dt_socket,server=y,suspend={0},address=127.0.0.1:{1}'.format('y' if options.suspend else 'n', options.port))
            elif options.debug_mode:
                args.insert(1, '--debug')

        where_conditions = []
        if options.fixture:
            where_conditions.append('test =~ .*{}.*'.format(options.fixture))
        if options.exclude:
            for category in options.exclude:
                where_conditions.append('cat != {}'.format(category))

        if where_conditions:
            args.append('--where= ' + ' and '.join(['({})'.format(x) for x in where_conditions]))

        if options.run_gdb:
            args = ['gdb', '-ex', 'handle SIGXCPU SIG33 SIG35 SIG36 SIGPWR nostop noprint', '--args'] + args

        process = subprocess.Popen(args, cwd=options.results_directory)
        process.wait()
        return process.returncode == 0

    def cleanup(self, options):
        NUnitTestSuite.instances_count -= 1
        if NUnitTestSuite.instances_count == 0:
            # merge nunit results
            print("Aggregating all nunit results")
            output = os.path.join(options.results_directory, 'nunit_output.xml')
            nunit_results_merger.merge(NUnitTestSuite.output_files, output)
            print('Output:  {}'.format(output))

