import commands
import os
import time
import re
import tempfile
from urlparse import urlparse
from datetime import datetime
import string
from collections import namedtuple
import pexpect
from nose.tools import assert_equals, assert_true, assert_false
from pprint import pformat
import conf
from lettuce import world
from IPy import IP

# Make Bash an object

world.instances = {}
world.images = {}
world.volumes = {}
world.floating = {}

timeout=60
poll_interval=5


DEFAULT_FIXTURE = [
      ('role', 'add', 'Admin'),
      ('role', 'add', 'KeystoneServiceAdmin'),
      ('role', 'add', 'Member'),
      #  Services
      ('service', 'add', 'swift', 'object-store', 'Swift-compatible service'),
      ('service', 'add', 'nova',  'compute', 'OpenStack Compute Service'),
      ('service', 'add', 'nova_billing', 'nova_billing', 'Billing for OpenStack'),
      ('service', 'add', 'glance', 'image', 'OpenStack Image Service'),
      ('service', 'add', 'identity', 'identity', 'OpenStack Identity Service'),
]

ENDPOINT_TEMPLATES = {
      "swift": ('http://%host%:8080/v1', 'http://%host%:8080/v1', 'http://%host%:8080/v1', '1', '0'),
      "nova": ('http://%host%:8774/v1.1/%tenant_id%', 'http://%host%:8774/v1.1/%tenant_id%', 'http://%host%:8774/v1.1/%tenant_id%', '1', '0'),
      "glance": ('http://%host%:9292/v1', 'http://%host%:9292/v1', 'http://%host%:9292/v1', '1', '0'),
      "nova_billing": ('http://%host%:8787', 'http://%host%:8787', 'http://%host%:8787', '1', '1'),
      "identity": ('http://%host%:5000/v2.0', 'http://%host%:35357/v2.0', 'http://%host%:5000/v2.0', '1', '1'),
}

def wait(timeout=timeout, poll_interval=poll_interval):
    def decorate(fcn):
        def f_retry(*args, **kwargs):
            time_left = timeout
            while time_left > 0:
                if fcn(*args, **kwargs): # make attempt
                    return True
                time.sleep(poll_interval)
                time_left -= poll_interval
            return False
        return f_retry
    return decorate

class command_output(object):
    def __init__(self, output):
        self.output = output

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

class bash(command_output):
    last_error_code = 0

    @classmethod
    def get_last_error_code(cls):
        return cls.last_error_code

    def __init__(self, cmdline):
        output = self.__execute(cmdline)
        super(bash,self).__init__(output)
        bash.last_error_code = self.output[0]

    def __execute(self, cmd):
        retcode = commands.getstatusoutput(cmd)
        status, text = retcode
        conf.bash_log(cmd, status, text)

#        print "------------------------------------------------------------"
#        print "cmd: %s" % cmd
#        print "sta: %s" % status
#        print "out: %s" % text

        return retcode



class rpm(object):

    @staticmethod
    def clean_all_cached_data():
        out = bash("sudo yum -q clean all")
        return out.successful()

    @staticmethod
    def install(package_list):
        out = bash("sudo yum -y install %s" % " ".join(package_list))
        return out.successful()

    @staticmethod
    def installed(package_list):
        out = bash("rpmquery %s" % " ".join(package_list))
        return out.successful() and not out.output_contains_pattern('not installed')

    @staticmethod
    def available(package_list):
        out = bash("sudo yum list %s" % " ".join(package_list))
        if not out.successful():
            return False
        lines = out.output_text().split("\n")
        for package in package_list:
            found = False
            for line in lines:
                if line.startswith("%s." % package):
                    found = True
                    break
            if not found:
                return False

        return True
        
    @staticmethod
    def remove(package_list):
        out = bash("sudo yum -y erase %s" % " ".join(package_list))
#        wildcards_stripped_pkg_name = package.strip('*')
        wildcards_stripped_pkg_name = " ".join(package_list)
#        return out.output_contains_pattern("(No Match for argument)|(Removed:[\s\S]*%s.*)|(Package.*%s.*not installed)" % (wildcards_stripped_pkg_name , wildcards_stripped_pkg_name))
        return out.successful()

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
enabled=0
gpgcheck=1

""".format(repo_id=repo)
        else:
            repo_config = """
[{repo_id}]
name=Grid Dynamics OpenStack RHEL
baseurl=http://osc-build.vm.griddynamics.net/unstable/{env}/{repo_id}
enabled=0
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
    def update_root_pwd( default_pwd="", admin_pwd="root"):
        out = bash('mysqladmin -u root password %s' %  admin_pwd)
        return out.successful()

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
        self.__unusual_running_patterns = {'rabbitmq-server': '(Node.*running)|(running_applications)'}
        self.__unusual_stopped_patterns = {'rabbitmq-server': 'no.nodes.running|no_nodes_running|nodedown|unrecognized'}
        self.__exec_by_expect = set(['rabbitmq-server'])

    def __exec_cmd(self, cmd):
        if self.__name in self.__exec_by_expect:
            return expect_run(cmd)

        return bash(cmd)

    def start(self):
        return self.__exec_cmd("sudo service %s start" % self.__name)

    def stop(self):
        return self.__exec_cmd("sudo service %s stop" % self.__name)

    def restart(self):
        return self.__exec_cmd("sudo service %s restart" % self.__name)

    def running(self):
        out = self.__exec_cmd("sudo service %s status" % self.__name)

        if self.__name in self.__unusual_running_patterns:
            return out.output_contains_pattern(self.__unusual_running_patterns[self.__name])

        return out.successful() \
            and out.output_contains_pattern("(?i)running") \
            and (not out.output_contains_pattern("(?i)stopped|unrecognized|dead|nodedown"))

    def stopped(self):
#        out = bash("sudo service %s status" % self.__name)
#        unusual_service_patterns = {'rabbitmq-server': 'no.nodes.running|no_nodes_running|nodedown'}
        out = self.__exec_cmd("sudo service %s status" % self.__name)

        if self.__name in self.__unusual_stopped_patterns:
            return out.output_contains_pattern(self.__unusual_stopped_patterns[self.__name])

        return (not out.output_contains_pattern("(?i)running")) \
            and out.output_contains_pattern("(?i)stopped|unrecognized|dead|nodedown")


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

    def remove_flags(self, flags):
        for name in flags:
            del self.options[name]
        return self

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

    def verify_existance(self, flags):
        for name in flags:
            name = name.strip()
            if name not in self.options:
                return False
        return True

    def overwrite(self, filename):
        return EscalatePermissions.overwrite(filename, self)

class novarc(dict):
    def __init__(self):
        super(novarc,self).__init__()

    def load(self, file):
        self.file = file
        return os.path.exists(file)

    def source(self):
        return "source %s" % self.file

    def bash(self, cmd):
        return bash('source %s && %s' % (self.file, cmd))

    @staticmethod
    def from_zipfile(project, user, destination):
        path = os.path.join(destination, 'novarc.zip')
        out = bash('sudo nova-manage project zipfile %s %s %s' % (project, user, path))
        if out.successful():
            out = bash("unzip -uo %s -d %s" % (path,destination))
            new_novarc = novarc()
            if out.successful() and new_novarc.load(os.path.join(destination, 'novarc')):
                return new_novarc
        return None

    @staticmethod
    def from_template(project, user, password, destination):
        new_novarc = novarc()
        path = os.path.join(destination, "novarc.template")

        novarc_template = open(path, "rt").read()
        novarc_text = novarc_template % {
            "auth_url": "http://127.0.0.1:5000/v2.0",
            "username": user,
            "tenant_name": project,
            "password": password}
        novarc_path = os.path.join(destination, 'novarc')
        open(novarc_path, "wt").write(novarc_text)
        if new_novarc.load(novarc_path):
            return new_novarc
        return None

    @staticmethod
    def create(project, user, password, destination):
        if os.path.exists("/etc/keystone"):
            return novarc.from_template(project, user, password, destination)
        else:
            return novarc.from_zipfile(project, user, destination)


        ##===================##
        ##  KEYSTONE MANAGE  ##
        ##===================##

class keystone_manage(object):
    @staticmethod
    def init_default(host='127.0.0.1', user='admin', password='secrete',tenant='systenant', token='111222333444', region='regionOne'):
        for cmd in DEFAULT_FIXTURE:
            bash("sudo keystone-manage %s" % ' '.join(cmd))

        keystone_manage.create_tenant(tenant)

        i=int(1)
        for service in ENDPOINT_TEMPLATES:
            keystone_manage.add_template(
                region, service,
                *[word.replace("%host%", host)
                  for word in ENDPOINT_TEMPLATES[service]])

# ___ TODO ___
# FIX IT
            keystone_manage.add_endpoint(tenant,i)
            i=i+1
        return True

    @staticmethod
    def create_tenant(name):
        out = bash("sudo keystone-manage tenant add %s" % name)
        return out.successful()

    @staticmethod
    def check_tenant_exist(name):
        out = bash("sudo keystone-manage tenant list|grep %s" % name ).output_text()
        if out.split()[1]:
            return True
        return False

    @staticmethod
    def delete_tenant(name):
        out = bash("sudo keystone-manage tenant delete %s" % name)
        return out.successful()

    @staticmethod
    def create_user(name,password,tenant=''):
        out = bash("sudo keystone-manage user add %s %s %s" % (name,password,tenant))
        return out.successful()

    @staticmethod
    def check_user_exist(name):
        out = bash("sudo keystone-manage user list|grep %s" % name ).output_text()
        if out.split()[1]:
            return True
        return False

    @staticmethod
    def delete_user(name):
        out = bash("sudo keystone-manage user delete %s" % name)
        return out.successful()

    @staticmethod
    def add_role(name):
        out = bash("sudo keystone-manage role add %s" % name)
        return out.successful()

    @staticmethod
    def check_role_exist(name):
        out = bash("sudo keystone-manage role list|grep %s" % name ).output_text()
        if out.split()[1]:
            return True
        return False

    @staticmethod
    def delete_role(name):
        out = bash("sudo keystone-manage role delete %s" % name)
        return out.successful()

    @staticmethod
    def grant_role(role, user):
        out = bash("sudo keystone-manage role grant %s %s" % (role,user))
        return out.successful()

#__ TODO __
    @staticmethod
    def check_role_granted(role, user):
        #out = bash("sudo keystone-manage role grant %s %s" % (role,user))
        return True

    @staticmethod
    def revoke_role(role, user):
        out = bash("sudo keystone-manage role revoke %s %s" % (role,user))
        return out.successful()

    @staticmethod
    def add_template(region='', service='', publicURL='', adminURL='', internalURL='', enabled='1', isglobal='1'):
        out = bash("sudo keystone-manage endpointTemplates add %s %s %s %s %s %s %s" % (region, service, publicURL, adminURL, internalURL, enabled, isglobal))
        return out.successful()

    @staticmethod
    def delete_template(region='', service='', publicURL='', adminURL='', internalURL='', enabled='1', isglobal='1'):
        out = bash("sudo keystone-manage endpointTemplates delete %s %s %s %s %s %s %s" % (region, service, publicURL, adminURL, internalURL, enabled, isglobal))
        return out.successful()

    @staticmethod
    def add_token(user, tenant, token='111222333444', expiration='2015-02-05T00:00'):
        out = bash("sudo keystone-manage token add %s %s %s %s" % (token, user, tenant, expiration))
        return out.successful()

#__ TODO __ (convert id to names, check it)
    @staticmethod
    def check_token_exist(user, tenant, token='111222333444', expiration='2015-02-05T00:00'):
        out = bash("sudo keystone-manage token list|grep %s" % token ).output_text()
        if out.split()[0]==token:
            return True
        return False


    @staticmethod
    def delete_token(user, tenant, token='111222333444', expiration='2015-02-05T00:00'):
        out = bash("sudo keystone-manage token delete %s" % token)
        return out.successful()

    @staticmethod
    def add_endpoint(tenant, template):
        out = bash("sudo keystone-manage endpoint add %s %s" % (tenant, template))
        return out.successful()

    @staticmethod
    def delete_endpoint(tenant, template):
        out = bash("sudo keystone-manage endpoint delete %s %s" % (tenant, template))
        return out.successful()



        ##===============##
        ##  NOVA MANAGE  ##
        ##===============##

class nova_manage(object):
    @staticmethod
    def floating_add_pool(cidr):
        return bash('sudo nova-manage floating create %s' % cidr)

    @staticmethod
    def floating_remove_pool(cidr):
        return bash('sudo nova-manage floating delete %s' % cidr)

    @staticmethod
    def floating_check_pool(cidr):
        out = bash('sudo nova-manage floating list').output_text()
        ips=IP(cidr)

        for addr in ips:
            ip=IP(addr).strNormal()
            for line in out.split('\n'):
                if ip in line.split()[1]:
                    return True
        return False

    @staticmethod
    def vm_image_register(image_name, owner, disk, ram, kernel):
        if (ram and kernel) not in ('', None):
            out = bash('sudo nova-manage image all_register --image="%s" --kernel="%s" --ram="%s" --owner="%s" --name="%s"'
                % (disk, kernel, ram, owner, image_name))
        else:
            out = bash('sudo nova-manage image image_register --path="%s" --owner="%s" --name="%s"'
                % (disk, owner, image_name))

        return out.successful()


        ##============##
        ##  NOVA CLI  ##
        ##============##


class nova_cli(object):

    __novarc = None

    @staticmethod
    def novarc_available():
        return not (nova_cli.__novarc is None)

    @staticmethod
    def get_novarc_load_cmd():
        if nova_cli.novarc_available():
            return nova_cli.__novarc.source()

        return "/bin/false"

    @staticmethod
    def set_novarc(project, user, password, destination):
        if nova_cli.__novarc is None:
            nova_cli.__novarc = novarc.create(project, user, password, destination)

        return nova_cli.__novarc

    @staticmethod
    def create_admin(username):
        out = bash("sudo nova-manage user admin %s" % username)
        return out.successful()

    @staticmethod
    def remove_admin(username):
        out = bash("sudo nova-manage user delete %s" % username)
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
    def remove_project(project_name):
        out = bash("sudo nova-manage project delete %s" % project_name)
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
    def create_network_via_flags(flags_dict):
        params = ""
        for flag, value in flags_dict.items():
            params += " {flag}='{value}'".format(flag=flag, value=value)

        return bash('sudo nova-manage network create %s' % params).successful()

    @staticmethod
    def network_exists(cidr):
        out = bash('sudo nova-manage network list')
        return out.successful() and out.output_contains_pattern(".*%s.*" % cidr)


#___ TODO ____

    @staticmethod
    def vm_image_register(image_name, owner, disk, ram, kernel):
        print "TODO"
        return rootfs_id is not None

    @staticmethod
    def vm_image_registered(name):
        return nova_cli.exec_novaclient_cmd('image-list | grep "%s"' % name)

    @staticmethod
    def add_keypair(name, public_key=None):
        public_key_param = "" if public_key is None else "--pub_key %s" % public_key
        return nova_cli.exec_novaclient_cmd('keypair-add %s %s' % (public_key_param, name))

    @staticmethod
    def delete_keypair(name):
        return nova_cli.exec_novaclient_cmd('keypair-delete %s' % name)

    @staticmethod
    def keypair_exists(name):
        text = nova_cli.get_novaclient_command_out('keypair-list')
        if text:
            table = ascii_table(text)
            if table.select_values('Fingerprint','Name', name):
                return True
        return False


    @staticmethod
    def get_image_id_list(name):
        lines = nova_cli.get_novaclient_command_out("image-list | grep '%s\s' | awk '{print $2}'" % name)
        id_list = lines.split(os.linesep)
        return id_list

#    @staticmethod
#    def start_vm_instance(name, image_id, flavor_id, key_name=None):
#        key_name_arg = "" if key_name is None else "--key_name %s" % key_name
#        return nova_cli.exec_novaclient_cmd("boot %s --image %s --flavor %s %s" % (name, image_id, flavor_id, key_name_arg))


    @staticmethod
    def start_vm_instance(name, image_id, flavor_id, key_name=None, sec_groups=None):
        key_name_arg = "" if key_name is None else "--key_name %s" % key_name
        sgroup_arg = "" if sec_groups is None else "--security_groups %s" % sec_groups
        text = nova_cli.get_novaclient_command_out("boot %s --image %s --flavor %s %s %s" % (name, image_id, flavor_id, key_name_arg, sgroup_arg))
        if text:
            table = ascii_table(text)
            instance_id = table.select_values('Value', 'Property', 'id')
            if instance_id:
                world.instances[name] = instance_id[0]
                return True
        return False


    @staticmethod
    def start_vm_instance_return_output(name, image_id, flavor_id, key_name=None):
        key_name_arg = "" if key_name is None else "--key_name %s" % key_name
        text =  nova_cli.get_novaclient_command_out("boot %s --image %s --flavor %s %s" % (name, image_id, flavor_id, key_name_arg))
        if text and bash.get_last_error_code() == 0:
            table = ascii_table(text)
            instance_id = table.select_values('Value', 'Property', 'id')
            if instance_id:
                world.instances[name] = instance_id[0]
            return ascii_table(text)
        return None


    @staticmethod
    def stop_vm_instance(name):
        return nova_cli.exec_novaclient_cmd("delete %s" % world.instances[name])


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
        text = nova_cli.get_novaclient_command_out("list")
        if text:
            table = ascii_table(text)
            try:
                status = table.select_values('Status', 'ID',world.instances[name])[0]
                return status
            except:
                return False
        return False

    @staticmethod
    def get_instance_ip(name):
        text = nova_cli.get_novaclient_command_out("list")
        if text:
            table = ascii_table(text)
            (status,ip) = table.select_values('Networks', 'ID',world.instances[name])[0].split('=')
            ip = ip.split(',')[0]
            return ip
        return False

    @staticmethod
#    @wait - TODO
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

    @staticmethod
    @wait()
    def wait_instance_stopped(name, timeout):
        if not nova_cli.get_instance_status(name):
            return True
        return False

    @staticmethod
    def billed_objects(project, min_instances, min_images):
        out = nova_cli.__novarc.bash("nova2ools-billing list --images --instances | grep '^Project %s$' -A 4" % project)
        if not out.successful():
            return False
        lines = out.output_text().split("\n")
        if len(lines) < 4:
            return False
        if not lines[1].startswith("instances:") or int(lines[1].split(" ")[1]) < min_instances:
            return False
        if not lines[3].startswith("images:") or int(lines[3].split(" ")[1]) < min_images:
            return False
        return True



    @staticmethod
    def floating_allocate(name):
        text = nova_cli.get_novaclient_command_out('floating-ip-create %s' % name)
        if text:
            table = ascii_table(text)
            world.floating[name] = table.select_values('Ip','Instance', 'None')[0]
            if world.floating[name]:return True
        return False

    @staticmethod
    def floating_deallocate(name):
        return nova_cli.exec_novaclient_cmd('floating-ip-delete %s' % world.floating[name])

    @staticmethod
    def floating_check_allocated(name):
        if not world.floating[name]: world.floating[name]=None
        text = nova_cli.get_novaclient_command_out('floating-ip-list')
        if text:
            table = ascii_table(text)
            try:
                value = table.select_values('Instance', 'Ip',  world.floating[name])[0]
                if value in ('None',):
                    return True
            except:
                return False
        return False


    @staticmethod
    def floating_associate(addr_name, ins_name):
        return nova_cli.exec_novaclient_cmd('add-floating-ip %s %s' % (world.instances[ins_name],world.floating[addr_name]))

    @staticmethod
    def floating_deassociate(addr_name, ins_name):
        return nova_cli.exec_novaclient_cmd('remove-floating-ip %s %s' % (world.instances[ins_name],world.floating[addr_name]))

    @staticmethod
    def floating_check_associated(addr_name, ins_name):
        if not world.floating[addr_name]: world.floating[addr_name]=None
        text = nova_cli.get_novaclient_command_out('floating-ip-list')

        if text:
            table = ascii_table(text)
            if table.select_values('Instance', 'Ip', world.floating[addr_name])[0]==world.instances[ins_name]:
                return True
        return False



        ##============##
        ##  EUCA CLI  ##
        ##============##


class euca_cli(object):
    
    @staticmethod
    def _parse_rule(dst_group=None, source_group_user=None,source_group=None, proto=None, source_subnet=None, port=None):
        params={}
        if dst_group: dst_group=str(dst_group)
        if source_group_user: source_group_user=str(source_group_user)
        if source_group: source_group=str(source_group)

        if port:
            try:
                if not port=='-1--1':
                    from_port, to_port = port.split('-')
            except:
                port=port+"-"+port


        if proto:
            proto=str(proto)
            if proto.upper() in ('ICMP',):
                if port in ('-1', '-1:-1','-1--1', '', None):
                    params['protocol']="icmp"
                    params['icmp-type-code']="-1:-1"
                else:
                    params['protocol']='icmp'
                    params['icmp-type-code']=port
            if proto.upper() in ('TCP', 'UDP'):
                params['protocol']=proto
                params['port-range']=port

        if source_subnet:
            if source_subnet in ('', None, '0', 'any'):
                params['source-subnet']='0.0.0.0/0'
            else:
                params['source-subnet']=source_subnet

        if source_group:
            params['source-group']=source_group

        if source_group_user:
            params['source-group-user']=source_group_user

        cmdline=[]
        for param,val in sorted(params.iteritems()):
            cmdline.append(' --'+param+' '+val)

        if dst_group:
            cmdline.append(' '+dst_group)
        else:
            cmdline.append(' default')

#        print "\nPARSE-PARAMS: %s"  % cmdline
        return ''.join(cmdline)


    @staticmethod
    def volume_create(name,size,zone='nova'):
        source = nova_cli.get_novarc_load_cmd()
        out = bash("%s && euca-create-volume --size %s --zone %s|grep VOLUME| awk '{print $2}'" % (source, size, zone))
        if out:
            euca_id = out.output_text().split()[0] 
            world.volumes[name] = misc.get_nova_id(euca_id)
        return out.successful()

    @staticmethod
    def get_volume_status(volume_name):
        source = nova_cli.get_novarc_load_cmd()
        volume_id='vol-'+misc.get_euca_id(nova_id=world.volumes[volume_name])
        out = bash("%s && euca-describe-volumes |grep %s" % (source,volume_id)).output_text()

        badchars=['(', ')', ',']
        for char in badchars:
            out=out.replace(char, ' ')
        k=1
        status={}
        values=out.split()
        if values:
            for key in ('volume_id', 'size', 'zone', 'status', 'project', 'host', 'instance', 'device', 'date'):
                status[key]=values[k]
                k=k+1
            if status['instance'] != 'None':
                ins = status['instance']
                ins = ins.replace(']','')
                status['instance'], status['instance-host'] = ins.split('[')
        if status: return status
        else: return False


    @staticmethod
    @wait()
    def wait_volume_comes_up(volume_name, timeout):
        status = euca_cli.get_volume_status(volume_name)['status']
        if 'available' in status:
            return True
        return False

    @staticmethod
    def volume_attach(instance_name, dev, volume_name):
        source = nova_cli.get_novarc_load_cmd()
        volume_id='vol-'+misc.get_euca_id(nova_id=world.volumes[volume_name])
        instance_id='i-'+misc.get_euca_id(nova_id=world.instances[instance_name])
        out = bash('%s && euca-attach-volume --instance %s --device %s %s' % (source, instance_id, dev, volume_id))
        return out.successful()

    @staticmethod
    @wait(120)
    def volume_attached_to_instance(volume_name, instance_name):
        volume_id='vol-'+misc.get_euca_id(nova_id=world.volumes[volume_name])
        instance_id='i-'+misc.get_euca_id(nova_id=world.instances[instance_name])
        status = euca_cli.get_volume_status(volume_name)
        if ('in-use' in status['status']) and (instance_id in status['instance']):
            return True
        return False

    @staticmethod
    def volume_detach(volume_name):
        source = nova_cli.get_novarc_load_cmd()
        volume_id='vol-'+misc.get_euca_id(nova_id=world.volumes[volume_name])
        out = bash('%s && euca-detach-volume %s' % (source,volume_id))
        time.sleep(30)
        return out.successful()

    @staticmethod
    @wait()
    def check_volume_deleted(volume_name):
        if not euca_cli.get_volume_status(volume_name):
            return True
        return False

    @staticmethod
    def volume_delete(volume_name):
        source = nova_cli.get_novarc_load_cmd()
        volume_id='vol-'+misc.get_euca_id(nova_id=world.volumes[volume_name])
        out = bash("%s && euca-delete-volume %s" % (source,volume_id))
        return out.successful()

    @staticmethod
    def sgroup_add(group_name):
        return bash('%s && euca-add-group -d smoketest-secgroup-test %s' % (nova_cli.get_novarc_load_cmd(),group_name)).successful()

    @staticmethod
    def sgroup_delete(group_name):
        return bash('%s && euca-delete-group %s' % (nova_cli.get_novarc_load_cmd(),group_name)).successful()

    @staticmethod
    def sgroup_check(group_name):
        out = bash("%s && euca-describe-groups %s |grep GROUP |awk '{print $3}'" % (nova_cli.get_novarc_load_cmd(),group_name)).output_text()
        if group_name in out:
            return True
        return False

    @staticmethod
    def sgroup_add_rule(dst_group='', src_group='', src_proto='', src_host='', dst_port=''):
        params = euca_cli._parse_rule(dst_group, '', src_group, src_proto, src_host, dst_port)
        return bash('%s && euca-authorize %s' % (nova_cli.get_novarc_load_cmd(),params)).successful()

    @staticmethod
    def sgroup_del_rule(dst_group='', src_group='', src_proto='', src_host='', dst_port=''):
        params = euca_cli._parse_rule(dst_group, '', src_group, src_proto, src_host, dst_port)
        return bash('%s && euca-revoke %s' % (nova_cli.get_novarc_load_cmd(),params)).successful()


    @staticmethod
    def sgroup_check_rule_exist(dst_group='', src_group='', src_proto='', src_host='', dst_port=''):
        out=bash('%s && euca-describe-groups %s|grep PERMISSION' % (nova_cli.get_novarc_load_cmd(),dst_group)).output_text()
        rule = euca_cli._parse_rule(dst_group, '', src_group, src_proto, src_host, dst_port)
#        print "Searching: "+rule

        # Try to assign to vars values as in euca-authorize output
        if out:
            for line in out.split('\n'):
#                print "Got line: "+line
                if 'FROM' in line:
                    (gperm, gproj, ggroup, grule, gproto, gport_from, gport_to, gfr, gci, ghost)=line.split()
#                    print "FR-OUT-line: "+euca_cli._parse_rule(ggroup, '', '', gproto, ghost, gport_from+"-"+gport_to)
                    if rule == euca_cli._parse_rule(ggroup, '', '', gproto, ghost, gport_from+"-"+gport_to):
                        return True

                elif 'GRPNAME' in line:
                    try:
                        (gperm, gproj, ggroup, grule, gproto, gport_from, gport_to, ggr, gsrc_group)=line.split()
#                        print "GR-OUT-line: "+euca_cli._parse_rule(ggroup, '', gsrc_group, gproto, '', gport_from+"-"+gport_to)
                        if rule == euca_cli._parse_rule(ggroup, '', gsrc_group, gproto, '', gport_from+"-"+gport_to):
                            return True
                    except:
                        return False
        return False

    @staticmethod
    def sgroup_check_rule(dst_group='', src_group='', src_proto='', src_host='', dst_port=''):
        # Workaround for group rule
        #PERMISSION      project1        smoketest3      ALLOWS  icmp    -1      -1      USER    project1
        #PERMISSION      project1        smoketest3      ALLOWS  tcp     1       65535   USER    project1
        #PERMISSION      project1        smoketest3      ALLOWS  udp     1       65536   USER    project1

        if src_group and (src_proto=='' and src_host=='' and dst_port==''):
            if euca_cli.sgroup_check_rule_exist(dst_group, src_group, src_proto='tcp', src_host='', dst_port='1-65535') and\
            euca_cli.sgroup_check_rule_exist(dst_group, src_group, src_proto='udp', src_host='', dst_port='1-65536') and \
            euca_cli.sgroup_check_rule_exist(dst_group, src_group, src_proto='icmp', src_host='', dst_port='-1'):
                return True
            print "in if"
        return euca_cli.sgroup_check_rule_exist(dst_group, src_group, src_proto, src_host, dst_port)


        ##===================##
        ##  GLANCE           ##
        ##===================##


class glance_cli(object):
    @staticmethod
    def glance_add(image_file, format, **kwargs):
#        out = nova_cli.__novarc.bash(
        out = bash(
            'glance add disk_format=%s container_format=%s is_public=True %s < "%s"'
            % (format,
               format,
               " ".join(["%s=%s" % (key, value)
                         for key, value in kwargs.iteritems()]),
               image_file))
        if not out.successful() or not "Added new image with ID:" in out.output_text():
            return None
        return int(out.output_text().split(':')[1])


    @staticmethod
    def vm_image_register(image_name, owner, disk, ram, kernel):
        kernel_id = glance_cli.glance_add(kernel, "aki", name="%s_kernel" % image_name)
        if kernel_id is None:
            return False
        ramdisk_id = glance_cli.glance_add(kernel, "ari", name="%s_ramdisk" % image_name)
        if ramdisk_id is None:
            return False
        rootfs_id = glance_cli.glance_add(
            kernel, "ami", name=image_name, kernel_id=kernel_id, ramdisk_id=ramdisk_id)
        return rootfs_id is not None



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
    def generate_ssh_keypair(file):
        bash("rm -f %s" % file)
        return bash("ssh-keygen -N '' -f {file} -t rsa -q".format(file=file)).successful()

    @staticmethod
    def can_execute_sudo_without_pwd():
        out = bash("sudo -l")
        return out.successful() and out.output_nonempty() \
            and (out.output_contains_pattern("\(ALL\)(\s)*NOPASSWD:(\s)*ALL")
                or out.output_contains_pattern("User root may run the following commands on this host"))

    @staticmethod
    def create_loop_dev(loop_dev,loop_file,loop_size):
        return bash("dd if=/dev/zero of=%s bs=1024 count=%s" % (loop_file, int(loop_size)*1024*1024)).successful() and bash("sudo losetup %s %s" % (loop_dev,loop_file)).successful()

    @staticmethod
    def delete_loop_dev(loop_dev,loop_file=""):
        if not loop_file:
            loop_file = bash("sudo losetup %s | sed 's/.*(\(.*\)).*/\1/'" % loop_dev).output_text()[0]
        return bash("sudo losetup -d %s" % loop_dev).successful() 
        # and bash("rm -f %s" % loop_file).successful()

    @staticmethod
    def check_loop_dev_exist(loop_dev):
        out = bash("sudo pvscan -s | grep %s" % loop_dev).output_text()
        if loop_dev in out:
            return True
        return False

    @staticmethod
    def create_lvm(lvm_dev,lvm_group="nova-volumes"):
        return bash("sudo pvcreate %s" % lvm_dev).successful() and bash("sudo vgcreate %s %s" % (lvm_group,lvm_dev)).successful()

    @staticmethod
    def delete_lvm(lvm_dev,lvm_group="nova-volumes"):
        return bash("sudo vgremove -f %s" % lvm_group).successful() and bash("sudo pvremove -y -ff %s" % lvm_dev).successful()

    @staticmethod
    def check_lvm_available(lvm_dev,lvm_group="nova-volumes"):
        out = bash("sudo vgscan | grep %s" % lvm_group).output_text()
        out1 = bash("sudo pvscan | grep %s" % lvm_group).output_text()
        if lvm_group in out:
            if (lvm_dev in out1) and (lvm_group in out1):
                return True
        return False

    @staticmethod
    def get_euca_id(nova_id=None, name=None):
        if nova_id:
            return '{0:008x}'.format(int(nova_id))
        elif name:
            return 'TODO'
        else: return False

    @staticmethod
    def get_nova_id(euca_id=None, name=None):
        if euca_id:
            return int(euca_id.split('-')[1],16)
        elif name:
            return 'TODO'
        else: return False


class ascii_table(object):
    def __init__(self, str):
        self.titles, self.rows = self.__construct(str)


    def __construct(self, str):
        column_titles = None
        rows = []
        for line in str.splitlines():
            if '|' in line:
                row =  map(string.strip, line.strip('|').split('|'))
                if column_titles is None:
                    column_titles = [rw.split()[0] for rw in row]
                else:
                    rows.append(row)
#        print "rows:"
#        print rows
#        print "tit:"
#        print column_titles
        Row = namedtuple('Row', column_titles)
        rows = map(Row._make, rows)
        return column_titles, rows

    def select_values(self, from_column, where_column, items_equal_to):
        from_column_number = self.titles.index(from_column.split()[0])
        where_column_name_number = self.titles.index(where_column.split()[0])
        return [item[from_column_number] for item in self.rows if item[where_column_name_number] == items_equal_to]

class expect_spawn(pexpect.spawn):
    def get_output(self, code_override=None):
        text_output = "before:\n{before}\nafter:\n{after}".format(
            before = self.before if isinstance(self.before, basestring) else pformat(self.before, indent=4),
            after = self.after if isinstance(self.after, basestring) else pformat(self.after, indent=4))

        if code_override is not None:
            conf.bash_log(pformat(self.args), code_override, text_output)
            return code_override, text_output

        if self.isalive():
            conf.bash_log(pformat(self.args), 'Spawned process running: pid={pid}'.format(pid=self.pid), text_output)
            raise pexpect.ExceptionPexpect('Unable to return exit code. Spawned command is still running:\n' + text_output)

        conf.bash_log(pformat(self.args), self.exitstatus, text_output)
        return self.exitstatus, text_output

class expect_run(command_output):
    def __init__(self, cmdline):
        output = self.__execute(cmdline)
        super(expect_run,self).__init__(output)

    def __execute(self, cmd):
        text, status = pexpect.run(cmd,withexitstatus=True)
        conf.bash_log(cmd, status, text)
        return status, text

class ssh(command_output):
    def __init__(self, host, command=None, user=None, key=None, password=None):

        options='-q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
        user_prefix = '' if user is None else '%s@' % user

        if key is not None: options += ' -i %s' % key

        cmd = "ssh {options} {user_prefix}{host} {command}".format(options=options,
                                                                   user_prefix=user_prefix,
                                                                   host=host,
                                                                   command=command)

        conf.log(conf.get_bash_log_file(),cmd)

        if password is None:
            super(ssh,self).__init__(bash(cmd).output)
        else:
            super(ssh,self).__init__(self.__use_expect(cmd, password))

    def __use_expect(self, cmd, password):
        spawned = expect_spawn(cmd)
        triggered_index = spawned.expect([pexpect.TIMEOUT, pexpect.EOF, 'password:'])
        if triggered_index == 0:
            return spawned.get_output(-1)
        elif triggered_index == 1:
            return spawned.get_output(-1)

        spawned.sendline(password)
        triggered_index = spawned.expect([pexpect.EOF, pexpect.TIMEOUT])
        if triggered_index == 1:
            spawned.terminate(force=True)

        return spawned.get_output()


class networking(object):

    class http(object):
        @staticmethod
        def probe(url):
            return bash('curl --silent --head %s | grep "200 OK"' % url).successful()

        @staticmethod
        def get(url, destination="."):
            return bash('wget -nv --directory-prefix="%s" %s' % (destination, url)).successful()

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
        def open_port_serves_protocol(host, port, proto, timeout):
            start_time = datetime.now()
            while(datetime.now() - start_time).seconds < int(timeout):
                if bash('nmap -PN -p %s --open -sV %s | ' \
                        'grep -iE "open.*%s"' % (port, host, proto)).successful():
                    return True

    class ifconfig(object):
        @staticmethod
        def interface_exists(name):
            return bash('sudo ifconfig %s' % name).successful()

        @staticmethod
        def set(interface, options):
            return bash('sudo ifconfig {interface} {options}'.format(interface=interface, options=options)).successful()



    class brctl(object):
        @staticmethod
        def create_bridge(name):
            return bash('sudo brctl addbr %s' % name).successful()

        @staticmethod
        def delete_bridge(name):
            return networking.ifconfig.set(name, 'down') and bash('sudo brctl delbr %s' % name).successful()

        @staticmethod
        def add_interface(bridge, interface):
            return bash('sudo brctl addif {bridge} {interface}'.format(bridge=bridge, interface=interface)).successful()

    class ip(object):
        class addr(object):
            @staticmethod
            def show(param_string):
                return bash('sudo ip addr show %s' % param_string)

#decorator for performing action on step failure
def onfailure(*triggers):
    def decorate(fcn):
        def wrap(*args, **kwargs):
            try:
                retval = fcn(*args, **kwargs)
            except:
                for trigger in triggers:
                    trigger()
                raise
            return retval
        return wrap

    return decorate


class debug(object):
    @staticmethod
    def current_bunch_path():
        global __file__
        return conf.get_current_module_path(__file__)

    class save(object):
        @staticmethod
        def file(src, dst):
            def saving_function():
                bash("sudo dd if={src} of={dst}".format(src=src,dst=dst))
            return saving_function

        @staticmethod
        def command_output(command, file_to_save):
            def command_output_function():
                dst = os.path.join(debug.current_bunch_path(),file_to_save)
                conf.log(dst, bash(command).output_text())
            return command_output_function

        @staticmethod
        def nova_conf():
            debug.save.file('/etc/nova/nova.conf', os.path.join(debug.current_bunch_path(), 'nova.conf.log'))()

        @staticmethod
        def log(logfile):
            src = logfile if os.path.isabs(logfile) else os.path.join('/var/log', logfile)
            dst = os.path.basename(src)
            dst = os.path.join(debug.current_bunch_path(), dst if os.path.splitext(dst)[1] == '.log' else dst + ".log")
            return debug.save.file(src, dst)







