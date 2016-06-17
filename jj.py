import os
import sys
import jenkins
import yaml
import glob
import shutil

BRANCH_NAME = 'branch'
BUILD_COMMAND = 'build-command'
TEMPLATE_NAME='template'

BRANCH_BUILD_JOB='branch-build.xml'
PR_BUILD_JOB='pr-build.xml'

GENERATED_XML_DIRNAME = "generated-xml"
DEFAULT_CONFIG_FILE=os.path.join(os.getenv("HOME"), ".jenkins-jobs.yaml")
PROJECT_DEFAULTS_FILE=os.path.join(os.getcwd(), 'defaults.yaml')

class JenkinsJobs(object):
    def __init__(self, conf=None):
        sfile = conf or DEFAULT_CONFIG_FILE

        self.templates = None
        self.defaults = None

        self.config = {}
        if os.path.exists(sfile):
            with open(sfile) as f:
                self.config = yaml.load(f)
        else:
            raise "No configuration file found at: %s!" % sfile

        if 'username' not in self.config or 'token' not in self.config:
            raise "Configuration file must contain Jenkins 'url', 'username', and 'token'"

        self.url = self.config['url']
        self.server = jenkins.Jenkins(self.url, username=self.config['username'], password=self.config['token'])
        self.config.pop('token', None)

        self.generated_dir = os.path.join(os.getcwd(), GENERATED_XML_DIRNAME)
        if os.path.isdir(self.generated_dir):
            shutil.rmtree(self.generated_dir)
        os.makedirs(self.generated_dir)

    def get_existing(self):
        return self.server.get_all_jobs()

    def delete(self, name):
        self.server.delete_job(name)

    def load_project(self, yaml_file):
        self.init_defaults()
        project = self.defaults.copy()
        project.update(self.config)
        with open(yaml_file) as f:
            project.update(yaml.load(f))
        return project

    def init_defaults(self):
        if self.defaults is not None:
            return self.defaults

        self.defaults={}
        if os.path.exists(PROJECT_DEFAULTS_FILE):
            with open(PROJECT_DEFAULTS_FILE) as f:
                self.defaults = yaml.load(f)
        else:
            print "WARNING: No defaults found at: %s" % PROJECT_DEFAULTS_FILE

        return self.defaults

    def load_templates(self):
        if self.templates is not None:
            return self.templates

        self.templates = {}
        for templatefile in glob.glob('templates/*.xml'):
            key = os.path.splitext(os.path.basename(templatefile))[0]
            with open(templatefile) as f:
                self.templates[key] = f.read()
        return self.templates

    def create_or_update(self, name, jobxml):
        with open(os.path.join(self.generated_dir, "%s.xml" % name), 'w') as f:
            f.write(jobxml)

        try:
            if self.server.job_exists(name) is True:
                print "Updating: %s" % name
                self.server.reconfig_job(name, jobxml)
            else:
                print "Creating: %s" % name
                self.server.create_job(name, jobxml)
            return True
        except jenkins.JenkinsException as e:
            print "Failed: %s" % e
        return False

    def build(self, name):
        print "Triggering build: %s" % name
        self.server.build_job(name)


