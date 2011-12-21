import commands
import os
import string
import time
import re
import yaml
import tempfile
from urlparse import urlparse
from datetime import datetime

from nose.tools import assert_equals, assert_true, assert_false

#def assert_lettuce_sentence

#env_dir_path = ''
#bash_log = ''

def init(dir_path):
    global env_dir_path, bash_log
    env_dir_path = dir_path
    bash_log = os.path.join(env_dir_path, "bash.log")


def load_yaml_config(filename):
    with open(filename, 'r') as config_file:
        config = yaml.load(config_file)
        return config

def log(logfile, message):
    with open(logfile, 'a+b') as file:
        file.write('%s: %s\n' % (time.ctime(), message))


# Make Bash an object



class bash(object):
    def __init__(self, cmdline):
        self.output = self.__execute(cmdline)

    def __execute(self, cmd):
        log(bash_log, "[COMMAND] " + cmd)
        retcode = commands.getstatusoutput(cmd)
        log(bash_log, "[RETCODE] %s" % retcode[0])
        log(bash_log, "[OUTPUT]\n %s" % retcode[1])
        return retcode

    def successful(self):
        return self.output[0] == 0

    def output_contains_pattern(self, pattern):
        regex2match = re.compile(pattern)
        search_result = regex2match.search(self.output[1])
        return (not search_result is None) and len(search_result.group()) > 0

    def output_text(self):
        return self.output[1]

    def output_nonempty(self):
        return len(self.output) > 1 and len(self.output[1]) > 0

class rpm(object):

    @staticmethod
    def clean_all_cached_data():
        out = bash("sudo yum -q clean all")
        return out.successful()

    @staticmethod
    def install(package):
        out = bash("sudo yum -y install '%s'" % package)
        return out.successful() and out.output_contains_pattern("(Installed:[\s\S]*%s.*)|(Package.*%s.* already installed)" % (package, package))
        
    @staticmethod
    def remove(package):
        out = bash("sudo yum -y erase '%s'" % package)
        wildcards_stripped_pkg_name = package.strip('*')
        return out.output_contains_pattern("(No Match for argument)|(Removed:[\s\S]*%s.*)|(Package.*%s.*not installed)" % (wildcards_stripped_pkg_name , wildcards_stripped_pkg_name))

    @staticmethod
    def installed(package):
        out = bash("rpmquery %s" % package)
        return not out.output_contains_pattern('not installed')

    @staticmethod
    def available(package):
        out = bash("sudo yum list | grep '^%s'" % package)
        return out.successful() and out.output_nonempty()

    @staticmethod
    def yum_repo_exists(id):
        out = bash("sudo yum repolist | grep -E '^%s'" % id)
        return out.successful() and out.output_contains_pattern("%s" % id)


class EnvironmentRepoWriter(object):
    def __init__(self, repo, env_name=None):

        if env_name is None or env_name == 'master':
            repo_config = """
[{repo_id}]
name=Grid Dynamics OpenStack RHEL
baseurl=http://osc-build.vm.griddynamics.net/{repo_id}
enabled=1
gpgcheck=1

""".format(repo_id=repo)
        else:
            repo_config = """
[os-master-repo]
name=Grid Dynamics OpenStack RHEL
baseurl=http://osc-build.vm.griddynamics.net/{repo_id}
enabled=1
gpgcheck=1

[{repo_id}]
name=Grid Dynamics OpenStack RHEL
baseurl=http://osc-build.vm.griddynamics.net/{env}/{repo_id}
enabled=1
gpgcheck=1

""".format(repo_id=repo, env=env_name)
            pass

        self.__config = repo_config


    def write(self, file):
        file.write(self.__config)


class EscalatePermissions(object):

    @staticmethod
    def read(filename, reader):
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file_path = tmp_file.name
        out = bash("sudo dd if=%s of=%s" % (filename, tmp_file_path))

        with open(tmp_file_path, 'r') as tmp_file:
            reader.read(tmp_file)
        bash("rm -f %s" % tmp_file_path)
        return out.successful()

    @staticmethod
    def overwrite(filename, writer):
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            writer.write(tmp_file)
            tmp_file_path = tmp_file.name
        out = bash("sudo dd if=%s of=%s" % (tmp_file_path, filename))
        bash("rm -f %s" % tmp_file_path)
        return out.successful() and os.path.exists(filename)


class mysql_cli(object):
    @staticmethod
    def create_db(db_name, admin_name="root", admin_pwd="root"):
        bash("mysqladmin -u%s -p%s -f drop %s" % (admin_name, admin_pwd, db_name))
        out = bash("mysqladmin -u%s -p%s create %s" % (admin_name, admin_pwd, db_name))
        return out.successful()

    @staticmethod
    def execute(sql_command, admin_name="root", admin_pwd="root"):
        out = bash('echo "%s" | mysql -u%s -p%s mysql' % (sql_command, admin_name, admin_pwd))
        return out

    @staticmethod
    def grant_db_access_for_hosts(hostname,db_name, db_user, db_pwd, admin_name="root", admin_pwd="root"):
        sql_command =  "GRANT ALL PRIVILEGES ON %s.* TO '%s'@'%s' IDENTIFIED BY '%s';" % (db_name, db_user, hostname, db_pwd)
        return mysql_cli.execute(sql_command, admin_name, admin_pwd).successful()

    @staticmethod
    def grant_db_access_local(db_name, db_user, db_pwd, admin_name="root", admin_pwd="root"):
        sql_command =  "GRANT ALL PRIVILEGES ON %s.* TO %s IDENTIFIED BY '%s';" % (db_name, db_user, db_pwd)
        return mysql_cli.execute(sql_command, admin_name, admin_pwd).successful()

    @staticmethod
    def db_exists(db_name, admin_name="root", admin_pwd="root"):
        sql_command = "show databases;"
        out = mysql_cli.execute(sql_command, admin_name, admin_pwd)
        return out.successful() and out.output_contains_pattern("%s" % db_name)

    @staticmethod
    def user_has_all_privileges_on_db(username, db_name, admin_name="root", admin_pwd="root"):
        sql_command = "show grants for '%s'@'localhost';" %username
        out = mysql_cli.execute(sql_command, admin_name, admin_pwd)
        return out.successful() \
            and out.output_contains_pattern("GRANT ALL PRIVILEGES ON .*%s.* TO .*%s.*" % (db_name, username))

    @staticmethod
    def user_has_all_privileges_on_db(username, db_name, admin_name="root", admin_pwd="root"):
        sql_command = "show grants for '%s'@'localhost';" %username
        out = mysql_cli.execute(sql_command, admin_name, admin_pwd)
        return out.successful() \
            and out.output_contains_pattern("GRANT ALL PRIVILEGES ON .*%s.* TO .*%s.*" % (db_name, username))

class service(object):
    def __init__(self, name):
        self.__name = name

    def start(self):
        out = bash("sudo service %s start" % self.__name)
        return out.successful()

    def stop(self):
        out = bash("sudo service %s stop" % self.__name)
        return out.successful()

    def running(self):
        out = bash("sudo service %s status" % self.__name)
        return out.successful() \
            and out.output_contains_pattern("(?i)running") \
            and (not out.output_contains_pattern("(?i)stopped|unrecognized|dead"))

    def stopped(self):
        out = bash("sudo service %s status" % self.__name)
        unusual_service_patterns = {'rabbitmq-server': 'no.nodes.running'}

        if self.__name in unusual_service_patterns:
            return out.output_contains_pattern(unusual_service_patterns[self.__name])

        return (not out.output_contains_pattern("(?i)running")) \
            and out.output_contains_pattern("(?i)stopped|unrecognized|dead")




class FlagFile(object):
    COMMENT_CHAR = '#'
    OPTION_CHAR =  '='

    def __init__(self, filename):
        self.__commented_options = set()
        self.options = {}
        self.__load(filename)

    def read(self, file):
        for line in file:
            comment = ''
            if FlagFile.COMMENT_CHAR in line:
                line, comment = line.split(FlagFile.COMMENT_CHAR, 1)
            if FlagFile.OPTION_CHAR in line:
                option, value = line.split(FlagFile.OPTION_CHAR, 1)
                option = option.strip()
                value = value.strip()
                if comment:
                    self.__commented_options.add(option)
                self.options[option] = value


    def __load(self, filename):
        EscalatePermissions.read(filename, self)

    def commented(self, option):
        return option in self.__commented_options

    def uncomment(self, option):
        if option in self.options and option in self.__commented_options:
            self.__commented_options.remove(option)

    def comment_out(self, option):
        if option in self.options:
            self.__commented_options.add(option)

    def write(self,file):
        for option, value in self.options.iteritems():
            comment_sign = FlagFile.COMMENT_CHAR if option in self.__commented_options else ''
            file.write("%s%s=%s\n" % (comment_sign, option, value))

    def apply_flags(self, pairs):
        for name, value in pairs:
            self.options[name.strip()] = value.strip()
        return self

    def verify(self, pairs):
        for name, value in pairs:
            name = name.strip()
            value = value.strip()
            if name not in self.options or self.options[name] != value:
                return False

        return True

    def overwrite(self, filename):
        return EscalatePermissions.overwrite(filename, self)

class nova_cli(object):

    __novarc = None

    class novarc(dict):
        def __init__(self):
            super(nova_cli.novarc,self).__init__()
            self.file = ""

        def load(self, file):
            self.file = file
            return os.path.exists(file)

        def source(self):
            return "source %s" % self.file

    @staticmethod
    def novarc_available():
        return not (nova_cli.__novarc is None)

    @staticmethod
    def get_novarc_load_cmd():
        if nova_cli.novarc_available():
            return nova_cli.__novarc.source()

        return "/bin/false"

    @staticmethod
    def set_novarc(project, user, destination):
        if nova_cli.__novarc is None:
            new_novarc = nova_cli.novarc()
            path  = os.path.join(destination, 'novarc.zip')
            out = bash('sudo nova-manage project zipfile %s %s %s' % (project, user, path))
            if out.successful():
                out = bash("unzip -uo %s -d %s" % (path,destination))
                if out.successful() and new_novarc.load(os.path.join(destination, 'novarc')):
                    nova_cli.__novarc = new_novarc

        return nova_cli.__novarc

    @staticmethod
    def create_admin(username):
        out = bash("sudo nova-manage user admin %s" % username)
        return out.successful()

    @staticmethod
    def user_exists(username):
        out = bash("sudo nova-manage user list")
        return out.successful() and out.output_contains_pattern(".*%s.*" % username)

    @staticmethod
    def create_project(project_name, username):
        out = bash("sudo nova-manage project create %s %s" % (project_name, username))
        return out.successful()

    @staticmethod
    def project_exists(project):
        out = bash("sudo nova-manage project list")
        return out.successful() and out.output_contains_pattern(".*%s.*" % project)

    @staticmethod
    def user_is_project_admin(user, project):
        out = bash("sudo nova-manage project list --user=%s" % user)
        return out.successful() and out.output_contains_pattern(".*%s.*" % project)

    @staticmethod
    def create_network(cidr, nets, ips):
        out = bash('sudo nova-manage network create private "%s" %s %s' % (cidr, nets, ips))
        return out.successful()

    @staticmethod
    def network_exists(cidr):
        out = bash('sudo nova-manage network list')
        return out.successful() and out.output_contains_pattern(".*%s.*" % cidr)

    @staticmethod
    def vm_image_register(image_name, owner, disk, ram, kernel):
        out = bash('sudo nova-manage image all_register --image="%s" --kernel="%s" --ram="%s" --owner="%s" --name="%s"'
        % (disk, kernel, ram, owner, image_name))
        return out.successful()

    @staticmethod
    def vm_image_registered(name):
        return nova_cli.exec_novaclient_cmd('image-list | grep "%s"' % name)

    @staticmethod
    def add_keypair(name, public_key=None):
        public_key_param = "" if public_key is None else "--pub_key %s" % public_key
        return nova_cli.exec_novaclient_cmd('keypair-add %s %s' % (public_key_param, name))

    @staticmethod
    def keypair_exists(name):
        return nova_cli.exec_novaclient_cmd('keypair-list | grep %s' % name)

    @staticmethod
    def get_image_id_list(name):
        lines = nova_cli.get_novaclient_command_out("image-list | grep  %s | awk '{print $2}'" % name)
        id_list = lines.split(os.linesep)
        return id_list

    @staticmethod
    def start_vm_instance(name, image_id, flavor_id, key_name=None):
        key_name_arg = "" if key_name is None else "--key_name %s" % key_name
        return nova_cli.exec_novaclient_cmd("boot %s --image %s --flavor %s %s" % (name, image_id, flavor_id, key_name_arg))
         

    @staticmethod
    def get_flavor_id_list(name):
        lines = nova_cli.get_novaclient_command_out("flavor-list | grep  %s | awk '{print $2}'" % name)
        id_list = lines.split(os.linesep)
        return id_list


    @staticmethod
    def db_sync():
        out = bash("sudo nova-manage db sync")
        return out.successful()

    @staticmethod
    def exec_novaclient_cmd(cmd):
        if nova_cli.novarc_available():
            source = nova_cli.get_novarc_load_cmd()
            out = bash('%s && nova %s' % (source, cmd))
            return out.successful()
        return False

    @staticmethod
    def get_novaclient_command_out(cmd):
        if nova_cli.novarc_available():
            source = nova_cli.get_novarc_load_cmd()
            out = bash('%s && nova %s' % (source, cmd))
            garbage_list = ['DeprecationWarning', 'import md5', 'import sha']

            def does_not_contain_garbage(str_item):
                for item in garbage_list:
                    if item in str_item:
                        return False
                return True

            lines_without_warning = filter(does_not_contain_garbage, out.output_text().split(os.linesep))
            return string.join(lines_without_warning, os.linesep)
        return ""

    @staticmethod
    def get_instance_status(name):
        return nova_cli.get_novaclient_command_out("list | grep %s | sed 's/|.*|.*|\(.*\)|.*|/\\1/'" % name).strip()

    @staticmethod
    def get_instance_ip(name):
        command = "list | grep %s | sed -e 's/|.*|.*|.*|\(.*\)|/\\1/' | sed -r 's/(.*)((\\b[0-9]{1,3}\.){3}[0-9]{1,3}\\b)/\\2/'" % name
        return nova_cli.get_novaclient_command_out(command).strip()

    @staticmethod
    def wait_instance_comes_up(name, timeout):
        poll_interval = 5
        time_left = int(timeout)
        status = ""
        while time_left > 0:
            status =  nova_cli.get_instance_status(name).upper()
            if status != 'ACTIVE':
                time.sleep(poll_interval)
                time_left -= poll_interval
            else:
                break
        return status == 'ACTIVE'


class misc(object):

    @staticmethod
    def kill_process(name):
        bash("sudo killall  %s" % name).successful()
        return True

    @staticmethod
    def unzip(zipfile, destination="."):
        out = bash("unzip %s -d %s" % (zipfile,destination))
        return out.successful()

    @staticmethod
    def extract_targz(file, destination="."):
        out = bash("tar xzf %s -C %s" % (file,destination))
        return out.successful()

    @staticmethod
    def remove_files_recursively_forced(wildcard):
        out = bash("sudo rm -rf %s" % wildcard)
        return out.successful()

    @staticmethod
    def no_files_exist(wildcard):
        out = bash("sudo ls -1 %s | wc -l" % wildcard)
        return out.successful() and out.output_contains_pattern("(\s)*0(\s)*")

    @staticmethod
    def install_build_env_repo(repo, env_name=None):
        return EscalatePermissions.overwrite('/etc/yum.repos.d/os-env.repo', EnvironmentRepoWriter(repo,env_name))


    @staticmethod
    def can_execute_sudo_without_pwd():
        out = bash("sudo -l")
        return out.successful() and out.output_nonempty() \
            and (out.output_contains_pattern("\(ALL\)(\s)*NOPASSWD:(\s)*ALL")
                or out.output_contains_pattern("User root may run the following commands on this host"))



class ssh(bash):
    def __init__(self, host, command=None, user=None, key=None):
        options='-q -o StrictHostKeyChecking=no'
        user_prefix = '' if user is None else '%s@' % user
        if key is not None: options += ' -i %s' % key

        cmd = "ssh {options} {user_prefix}{host} {command}".format(options=options,
                                                                   user_prefix=user_prefix,
                                                                   host=host,
                                                                   command=command)
        super(ssh,self).__init__(cmd)




class networking(object):

    class http(object):
        @staticmethod
        def probe(url):
            return bash('curl --silent --head %s | grep "200 OK"' % url).successful()

        @staticmethod
        def get(url, destination="."):
            return bash('wget  --directory-prefix="%s" %s' % (destination, url)).successful()

        @staticmethod
        def basename(url):
            return os.path.basename(urlparse(url).path)

    class icmp(object):
        @staticmethod
        def probe(ip, timeout):
            start_time = datetime.now()
            while (datetime.now() - start_time).seconds < int(timeout):
                if bash("ping -c3 %s" % ip).successful():
                    return True
            return False

    class nmap(object):
        @staticmethod
        def open_port_serves_protocol(host, port, proto):
            return bash('nmap -PN -p %s --open -sV %s | grep -iE "open.*%s"' % (port, host, proto)).successful()


        
            


