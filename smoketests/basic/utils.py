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

# Make Bash an object

world.instances = {}
world.images = {}
world.volumes = {}


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
    def __init__(self, cmdline):
        output = self.__execute(cmdline)
        super(bash,self).__init__(output)

    def __execute(self, cmd):
        retcode = commands.getstatusoutput(cmd)
        status, text = retcode
        conf.bash_log(cmd, status, text)

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
        out = bash("sudo yum list | grep '^%s\.'" % package)
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
        self.__unusual_stopped_patterns = {'rabbitmq-server': 'no.nodes.running|no_nodes_running|nodedown'}
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
    def set_novarc(project, user, destination):
        if nova_cli.__novarc is None:
            new_novarc = novarc()
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

#    @staticmethod
#    def start_vm_instance(name, image_id, flavor_id, key_name=None):
#        key_name_arg = "" if key_name is None else "--key_name %s" % key_name
#        return nova_cli.exec_novaclient_cmd("boot %s --image %s --flavor %s %s" % (name, image_id, flavor_id, key_name_arg))


    @staticmethod
    def start_vm_instance(name, image_id, flavor_id, key_name=None):
        key_name_arg = "" if key_name is None else "--key_name %s" % key_name
        text = nova_cli.get_novaclient_command_out("boot %s --image %s --flavor %s %s" % (name, image_id, flavor_id, key_name_arg))
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
        if text:
            table = ascii_table(text)
            instance_id = table.select_values('Value', 'Property', 'id')
            if instance_id:
                world.instances[name] = instance_id[0]
            return ascii_table(text)
        return None


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
            return table.select_values('Status', 'ID',world.instances[name])[0]
        return False

    @staticmethod
    def get_instance_ip(name):
        text = nova_cli.get_novaclient_command_out("list")
        if text:
            table = ascii_table(text)
            (status,ip) = table.select_values('Networks', 'ID',world.instances[name])[0].split('=')
            return ip
        return False

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


class euca_cli(object):

    @staticmethod
    def volume_create(name,size,zone='nova'):
        out = bash("euca-create-volume --size %s --zone %s|grep VOLUME| awk '{print $2}'" % (size, zone))
        if out:
            euca_id = out.output_text().split()[0] 
            world.volumes[name] = misc.get_nova_id(euca_id)
        return out.successful()

    @staticmethod
    def get_volume_status(volume_name):
#        world.volumes[volume_name]=23
        volume_id='vol-'+misc.get_euca_id(nova_id=world.volumes[volume_name])
        out = bash("euca-describe-volumes |grep %s" % volume_id).output_text()

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
        return status


    @staticmethod
    def wait_volume_comes_up(volume_name, timeout):
        poll_interval = 5
        time_left = int(timeout)
        while time_left > 0:
            status = euca_cli.get_volume_status(volume_name)['status']
            if status != 'available':
                time.sleep(poll_interval)
                time_left -= poll_interval
            else:
                break
        return status == 'available'

    @staticmethod
    def volume_attach(instance_name, dev, volume_name):
        volume_id='vol-'+misc.get_euca_id(nova_id=world.volumes[volume_name])
        instance_id='i-'+misc.get_euca_id(nova_id=world.instances[instance_name])
        out = bash('euca-attach-volume --instance %s --device %s %s' % (instance_id, dev, volume_id))
        time.sleep(30)
        return out.successful()

    @staticmethod
    def volume_attached_to_instance(volume_name, instance_name):
        volume_id='vol-'+misc.get_euca_id(nova_id=world.volumes[volume_name])
        instance_id='i-'+misc.get_euca_id(nova_id=world.instances[instance_name])
        status = euca_cli.get_volume_status(volume_name)
        if ('in-use' in status['status']) and (instance_id in status['instance']):
            return True
        return False

    @staticmethod
    def volume_detach(volume_name):
        volume_id='vol-'+misc.get_euca_id(nova_id=world.volumes[volume_name])
        out = bash('euca-detach-volume %s' % volume_id)
        time.sleep(30)
        return out.successful()

    @staticmethod
    def wait_volume_deletes(volume_name, timeout):
        poll_interval = 5
        time_left = int(timeout)
        while time_left > 0:
            try:
                status = euca_cli.get_volume_status(volume_name)['status']
            except:
                return True
            if status == 'deleting':
                time.sleep(poll_interval)
                time_left -= poll_interval
            else:
                return False
        return False

    @staticmethod
    def volume_delete(name,size,zone='nova'):
        out = bash("euca-delete-volume %s")
        return out.successful()


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
        return bash("ssh-keygen -N '' -f {file} -t rsa -q".format(file=file)).successful()

    @staticmethod
    def can_execute_sudo_without_pwd():
        out = bash("sudo -l")
        return out.successful() and out.output_nonempty() \
            and (out.output_contains_pattern("\(ALL\)(\s)*NOPASSWD:(\s)*ALL")
                or out.output_contains_pattern("User root may run the following commands on this host"))

    @staticmethod
    def create_loop_dev(loop_dev,loop_file,loop_size):
        return bash("dd if=/dev/zero of=%s bs=1024 count=%s" % (loop_file, int(loop_size)*1024*1024)).successful() and bash("losetup %s %s" % (loop_dev,loop_file)).successful()

    @staticmethod
    def delete_loop_dev(loop_dev,loop_file=""):
        if not loop_file:
            loop_file = bash("losetup %s | sed 's/.*(\(.*\)).*/\1/'" % loop_dev).output_text()[0]
        return bash("losetup -d %s" % loop_dev).successful() and bash("rm -f %s" % loop_file).successful()

    @staticmethod
    def check_loop_dev_exist(loop_dev):
        out = bash("pvscan -s | grep %s" % loop_dev).output_text()
        if loop_dev in out:
            return True
        return False

    @staticmethod
    def create_lvm(lvm_dev,lvm_group="nova-volumes"):
        return bash("pvcreate %s" % lvm_dev).successful() and bash("vgcreate %s %s" % (lvm_group,lvm_dev)).successful()

    @staticmethod
    def delete_lvm(lvm_dev,lvm_group="nova-volumes"):
        return bash("vgremove -f %s" % lvm_group).successful() and bash("pvremove -y -ff %s" % lvm_dev).successful()

    @staticmethod
    def check_lvm_available(lvm_dev,lvm_group="nova-volumes"):
        out = bash("vgscan | grep %s" % lvm_dev).output_text()
        out1 = bash("pvscan | grep %s" % lvm_group).output_text()
        if lvm_dev in out:
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
                    column_titles = row
                else:
                    rows.append(row)

        Row = namedtuple('Row', column_titles)
        rows = map(Row._make, rows)
        return column_titles, rows

    def select_values(self, from_column, where_column, items_equal_to):
        from_column_number = self.titles.index(from_column)
        where_column_name_number = self.titles.index(where_column)
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

        options='-q -o StrictHostKeyChecking=no'
        user_prefix = '' if user is None else '%s@' % user

        #if password is None: options += ' -q'
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
        ssh_newkey = 'Are you sure you want to continue connecting'
        triggered_index = spawned.expect([pexpect.TIMEOUT, ssh_newkey, 'password:', pexpect.EOF])
        if triggered_index == 0:
            return spawned.get_output(-1)
        elif triggered_index == 1:
            spawned.sendline ('yes')
            triggered_index = spawned.expect([pexpect.TIMEOUT, 'password:'])
            if triggered_index == 0:
                return spawned.get_output(-1)
        elif triggered_index == 3:
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

