from lettuce import step, world
from nose.tools import assert_equals, assert_true, assert_false
import utils
import os
import bunch.special

path = os.path.abspath(__file__)
dir_path = os.path.dirname(path)
utils.init(dir_path)
config_file = os.path.join(dir_path, "config.yaml")
config = utils.load_yaml_config(config_file)
bunch_working_dir = dir_path

def dump(obj):
  for attr in dir(obj):
    print "obj.%s = %s" % (attr, getattr(obj, attr))

mysql_admin = config['db']['admin']
mysql_admin_pwd = config['db']['admin_pwd']

class step_assert(object):
    def __init__(self, step):
        self.step = step
    
    def assert_true(self, expr):
        msg = 'Step "%s" failed ' % self.step.sentence
        assert_true(expr, msg)
        
    def assert_false(self, expr):
        msg = 'Step "%s" failed ' % self.step.sentence
        assert_false(expr, msg)

@step(u'current user can execute sudo without password')
def check_current_user_sudo_nopwd(step):
    step_assert(step).assert_true(utils.misc.can_execute_sudo_without_pwd())

@step(u'every RPM package available:')
def check_rpm_available(step):
    for data in step.hashes:
        step_assert(step).assert_true(utils.rpm.available(data['PackageName']))

@step(u'I clean yum cached data')
def clean_yum_caches(step):
    step_assert(step).assert_true(utils.rpm.clean_all_cached_data())

@step(u'I setup OpenStack repository "(.*)" for environment "(.*)"')
def install_build_env_repo(step, repo, env_name):
    step_assert(step).assert_true(utils.misc.install_build_env_repo(repo, env_name))

@step(u'yum repository with id "(.*)" is configured')
def check_yum_repository_with_id_exists(step, id):
    step_assert(step).assert_true(utils.rpm.yum_repo_exists(id))

@step(u'I install RPM package\(s\):')
def install_rpm(step):
    utils.rpm.clean_all_cached_data()
    for data in step.hashes:
        step_assert(step).assert_true(utils.rpm.install(data['PackageName']))

@step(u'every RPM package is installed:')
def check_rpm_installed(step):
    for data in step.hashes:
        step_assert(step).assert_true(utils.rpm.installed(data['PackageName']))

@step(u'I remove RPM package\(s\):')
def remove_rpm(step):
    utils.rpm.clean_all_cached_data()
    for data in step.hashes:
        step_assert(step).assert_true(utils.rpm.remove(data['PackageName']))

@step(u'every RPM package is not installed:')
def check_rpm_not_installed(step):
    for data in step.hashes:
        step_assert(step).assert_false(utils.rpm.installed(data['PackageName']))

@step(u'I create MySQL database "(.*)"')
def create_mysql_db(step, db_name):
    step_assert(step).assert_true(utils.mysql_cli.create_db(db_name, mysql_admin, mysql_admin_pwd))

@step(u'I grant all privileges on database "(.*)" to user "(.*)" identified by password "(.*)" at hosts:')
def setup_mysql_access_for_hosts(step, db_name, db_user, db_pwd):
    for data in step.hashes:
        step_assert(step).assert_true(utils.mysql_cli.grant_db_access_for_hosts(data['Hostname'],db_name, db_user, db_pwd, mysql_admin, mysql_admin_pwd))

@step(u'I grant all privileges on database "(.*)" to user "(.*)" identified by password "(.*)" locally')
def setup_mysql_access_local(step, db_name, db_user, db_pwd):
    step_assert(step).assert_true(utils.mysql_cli.grant_db_access_local(db_name, db_user, db_pwd, mysql_admin, mysql_admin_pwd))
    step_assert(step).assert_true(utils.mysql_cli.grant_db_access_local(db_name, mysql_admin, mysql_admin_pwd, mysql_admin, mysql_admin_pwd))

@step(u'every service is running:')
def every_service_is_running(step):
    for data in step.hashes:
        step_assert(step).assert_true(utils.service(data['ServiceName']).running())

@step(u'I start services:')
def start_services(step):
    for data in step.hashes:
        step_assert(step).assert_true(utils.service(data['ServiceName']).start())


@step(u'MySQL database "(.*)" exists')
def mysql_db_exists(step, db_name):
    step_assert(step).assert_true(utils.mysql_cli.db_exists(db_name, mysql_admin, mysql_admin_pwd))


@step(u'user "(.*)" has all privileges on database "(.*)"')
def mysql_user_has_all_privileges(step, user, db_name):
    step_assert(step).assert_true(utils.mysql_cli.user_has_all_privileges_on_db(user, db_name, mysql_admin, mysql_admin_pwd))

@step(u'I perform Nova DB sync')
def perform_nova_db_sync(step):
    step_assert(step).assert_true(utils.nova_cli.db_sync())


@step(u'I stop services:')
def stop_services(step):
    for data in step.hashes:
        step_assert(step).assert_true(utils.service(data['ServiceName']).stop())

@step(u'every service is stopped:')
def every_service_is_stopped(step):
    for data in step.hashes:
        step_assert(step).assert_true(utils.service(data['ServiceName']).stopped())

@step(u'I clean state files:')
def clean_state_files(step):
    for data in step.hashes:
        step_assert(step).assert_true(utils.misc.remove_files_recursively_forced(data['PathWildCard']))

@step(u'no files exist:')
def no_files_exist(step):
    for data in step.hashes:
        step_assert(step).assert_true(utils.misc.no_files_exist(data['PathWildCard']))

@step(u'I change flag file "(.*)" by setting flag values:')
def change_flag_file(step,flag_file):
    flags = [(flag['Name'],flag['Value']) for flag in step.hashes ]
    step_assert(step).assert_true(utils.FlagFile(flag_file).apply_flags(flags).overwrite(flag_file))

    
@step(u'the following flags in file "(.*)" are set to:')
def verify_flag_file(step,flag_file):
    flags = [(flag['Name'],flag['Value']) for flag in step.hashes ]
    step_assert(step).assert_true(utils.FlagFile(flag_file).verify(flags))

@step(u'I create nova admin user "(.*)"')
def create_nova_admin(step, username):
    step_assert(step).assert_true(utils.nova_cli.create_admin(username))


@step(u'nova user "(.*)" exists')
def nova_user_exists(step, user):
    step_assert(step).assert_true(utils.nova_cli.user_exists(user))

@step(u'I create nova project "(.*)" for user "(.*)"')
def create_nova_project(step, name, user):
    step_assert(step).assert_true(utils.nova_cli.create_project(name, user))


@step(u'nova project "(.*)" exists')
def nova_project_exists(step, project):
    step_assert(step).assert_true(utils.nova_cli.project_exists(project))

@step(u'nova user "(.*)" is the manager of the nova project "(.*)"')
def nova_user_is_project_manager(step, user, project):
    step_assert(step).assert_true(utils.nova_cli.user_is_project_admin(user, project))


@step(u'I create nova network "(.*)" with "(.*)" nets, "(.*)" IPs per network')
def create_nova_network(step, cidr, nets, ips):
    step_assert(step).assert_true(utils.nova_cli.create_network(cidr, nets, ips))


@step(u'nova network "(.*)" exists')
def nova_network_exists(step, cidr):
    step_assert(step).assert_true(utils.nova_cli.network_exists(cidr))


@step(u'novarc for project "(.*)", user "(.*)" is available')
def novarc_is_available(step, project, user):
    utils.nova_cli.set_novarc(project, user, bunch_working_dir)
    step_assert(step).assert_true(utils.nova_cli.novarc_available())


@step(u'VM image tarball is available at "(.*)"')
def http_resource_is_availaable(step, url):
    step_assert(step).assert_true(utils.networking.http.probe(url))

@step(u'I download VM image tarball at "(.*)" and unpack it')
def download_tarball_then_unpack(step, url):
    step_assert(step).assert_true(utils.networking.http.get(url, bunch_working_dir))
    file = os.path.join(bunch_working_dir, utils.networking.http.basename(url))
    step_assert(step).assert_true(utils.misc.extract_targz(file, bunch_working_dir))

@step(u'I register VM image "(.*)" for owner "(.*)" using disk "(.*)", ram "(.*)", kernel "(.*)"')
def register_all_images(step, name, owner, disk, ram, kernel):
    step_assert(step).assert_true(utils.nova_cli.vm_image_register(name, owner,
                                                                    os.path.join(bunch_working_dir,disk),
                                                                    os.path.join(bunch_working_dir,ram),
                                                                    os.path.join(bunch_working_dir, kernel)))


@step(u'VM image "(.*)" is registered')
def image_registered(step, name):
    step_assert(step).assert_true(utils.nova_cli.vm_image_registered(name))

@step(u'I add keypair with name "(.*)"')
def add_keypair(step, name):
    step_assert(step).assert_true(utils.nova_cli.add_keypair(name, "~/.ssh/authorized_keys"))

@step(u'keypair with name "(.*)" exists')
def keypair_exists(step, name):
    step_assert(step).assert_true(utils.nova_cli.keypair_exists(name))

@step(u'I start VM instance "(.*)" using image "(.*)",  flavor "(.*)" and keypair "(.*)"')
def start_vm_instance(step, name,image, flavor, keyname):
    id_image_list = utils.nova_cli.get_image_id_list(image)
    assert_equals(len(id_image_list), 1, "There are %s images with name %s: %s" % (len(id_image_list), name, str(id_image_list)))
    id_flavor_list = utils.nova_cli.get_flavor_id_list(flavor)
    assert_equals(len(id_flavor_list), 1, "There are %s flavors with name %s: %s" % (len(id_flavor_list), name, str(id_flavor_list)))
    image_id = id_image_list[0]
    flavor_id = id_flavor_list[0]
    assert_true(image_id != '', image_id)
    assert_true(flavor_id != '', flavor_id)
    step_assert(step).assert_true(utils.nova_cli.start_vm_instance(name, image_id, flavor_id, keyname))

@step(u'I kill all processes:')
def kill_all_processes(step):
    for data in step.hashes:
        step_assert(step).assert_true(utils.misc.kill_process(data['Process']))


@step(u'VM instance "(.*)" comes up within "(.*)" seconds')
def wait_instance_comes_up_within(step, name, timeout):
    step_assert(step).assert_true(utils.nova_cli.wait_instance_comes_up(name, int(timeout)))

@step(u'VM instance "(.*)" is pingable within "(.*)" seconds')
def vm_is_pingable(step, name, timeout):
    ip = utils.nova_cli.get_instance_ip(name)
    assert_true(ip != '', name)
    step_assert(step).assert_true(utils.networking.icmp.probe(ip, int(timeout)))

@step(u'I check that "(.*)" port of VM instance "(.*)" is open and serves "(.*)" protocol')
def check_port_protocol(step, port, name, protocol):
    ip = utils.nova_cli.get_instance_ip(name)
    assert_true(ip != '', name)
    step_assert(step).assert_true(utils.networking.nmap.open_port_serves_protocol(ip, port, protocol))

@step(u'I can log into VM "(.*)" via SSH as "(.*)"')
def check_can_log_via_ssh(step, name, user):
    ip = utils.nova_cli.get_instance_ip(name)
    assert_true(ip != '', name)
    step_assert(step).assert_true(utils.ssh(ip, "exit", user).successful())