from lettuce import step, world
from nose.tools import assert_equals, assert_true, assert_false
import utils
from utils import onfailure
import os
import bunch.special
import conf

dir_path = conf.get_current_module_path(__file__)

conf.init(dir_path)
config_file = os.path.join(dir_path, "config.yaml")
config = conf.load_yaml_config(config_file)
bunch_working_dir = dir_path

def dump(obj):
  for attr in dir(obj):
    print "obj.%s = %s" % (attr, getattr(obj, attr))

mysql_admin = config['db']['admin']
mysql_admin_pwd = config['db']['admin_pwd']

class step_assert(object):
    def __init__(self, step):
        self.step = step

    def assert_equals(self, expr1, expr2, Msg=None):
        msg = 'Step "%s" failed ' % self.step.sentence
        if Msg is not None:
            msg += '\n' + Msg
        assert_equals(expr1, expr2, msg)

    def assert_true(self, expr):
        msg = 'Step "%s" failed ' % self.step.sentence
        assert_true(expr, msg)
        
    def assert_false(self, expr):
        msg = 'Step "%s" failed ' % self.step.sentence
        assert_false(expr, msg)


@step(u'sleep')
def sleep(step):
    time.sleep(400)

@step(u'current user can execute sudo without password')
def check_current_user_sudo_nopwd(step):
    step_assert(step).assert_true(utils.misc.can_execute_sudo_without_pwd())

@step(u'every RPM package available:')
def check_rpm_available(step):
    step_assert(step).assert_true(utils.rpm.available([data['PackageName'] for data in step.hashes]))

@step(u'I clean yum cached data')
def clean_yum_caches(step):
    step_assert(step).assert_true(utils.rpm.clean_all_cached_data())

@step(u'I setup OpenStack repository "(.*?)" for environment "(.*?)"')
def install_build_env_repo(step, repo, env_name):
    step_assert(step).assert_true(utils.misc.install_build_env_repo(repo, env_name))

@step(u'yum repository with id "(.*?)" is configured')
def check_yum_repository_with_id_exists(step, id):
    step_assert(step).assert_true(utils.rpm.yum_repo_exists(id))

@step(u'I install RPM package\(s\):')
def install_rpm(step):
    step_assert(step).assert_true(utils.rpm.install([data['PackageName'] for data in step.hashes]))

@step(u'every RPM package is installed:')
def check_rpm_installed(step):
    step_assert(step).assert_true(utils.rpm.installed([data['PackageName'] for data in step.hashes]))

@step(u'I remove RPM package\(s\):')
def remove_rpm(step):
    utils.rpm.clean_all_cached_data()
    step_assert(step).assert_true(utils.rpm.remove([data['PackageName'] for data in step.hashes]))

@step(u'every RPM package is not installed:')
def check_rpm_not_installed(step):
    step_assert(step).assert_false(utils.rpm.installed([data['PackageName'] for data in step.hashes]))

@step(u'I set MySQL root password to "(.*)"')
def create_mysql_db(step, admin_pwd):
    step_assert(step).assert_false(utils.mysql_cli.update_root_pwd(admin_pwd = admin_pwd))


@step(u'I create MySQL database "(.*?)"')
def create_mysql_db(step, db_name):
    step_assert(step).assert_true(utils.mysql_cli.create_db(db_name, mysql_admin, mysql_admin_pwd))

@step(u'I grant all privileges on database "(.*?)" to user "(.*?)" identified by password "(.*?)" at hosts:')
def setup_mysql_access_for_hosts(step, db_name, db_user, db_pwd):
    for data in step.hashes:
        step_assert(step).assert_true(utils.mysql_cli.grant_db_access_for_hosts(data['Hostname'],db_name, db_user, db_pwd, mysql_admin, mysql_admin_pwd))

@step(u'I grant all privileges on database "(.*?)" to user "(.*?)" identified by password "(.*?)" locally')
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

@step(u'I restart services:')
def restart_services(step):
    for data in step.hashes:
        step_assert(step).assert_true(utils.service(data['ServiceName']).restart())


@step(u'MySQL database "(.*?)" exists')
def mysql_db_exists(step, db_name):
    step_assert(step).assert_true(utils.mysql_cli.db_exists(db_name, mysql_admin, mysql_admin_pwd))


@step(u'user "(.*?)" has all privileges on database "(.*?)"')
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

@step(u'I change flag file "(.*?)" by setting flag values:')
def change_flag_file(step,flag_file):
    flags = [(flag['Name'],flag['Value']) for flag in step.hashes ]
    step_assert(step).assert_true(utils.FlagFile(flag_file).apply_flags(flags).overwrite(flag_file))

@step(u'I change flag file "(.*?)" by removing flag values:')
def change_flag_file(step,flag_file):
    flags = [(flag['Name']) for flag in step.hashes ]
    step_assert(step).assert_true(utils.FlagFile(flag_file).remove_flags(flags).overwrite(flag_file))

@step(u'the following flags in file "(.*?)" are set to:')
def verify_flag_file(step,flag_file):
    flags = [(flag['Name'],flag['Value']) for flag in step.hashes ]
    step_assert(step).assert_true(utils.FlagFile(flag_file).verify(flags))

@step(u'Then the following flags are not in "(.*?)":')
def verify_flag_not_exist_file(step,flag_file):
    flags = [(flag['Name']) for flag in step.hashes ]
    step_assert(step).assert_true(not utils.FlagFile(flag_file).verify_existance(flags))

@step(u'I create nova admin user "(.*?)"')
def create_nova_admin(step, username):
    step_assert(step).assert_true(utils.nova_cli.create_admin(username))

@step(u'I remove nova admin user "(.*?)"')
def remove_nova_admin(step, username):
    step_assert(step).assert_true(utils.nova_cli.remove_admin(username))

@step(u'nova user "(.*?)" exists')
def nova_user_exists(step, user):
    step_assert(step).assert_true(utils.nova_cli.user_exists(user))

@step(u'nova user "(.*?)" does not exists')
def nova_user_exists(step, user):
    step_assert(step).assert_false(utils.nova_cli.user_exists(user))

@step(u'I create nova project "(.*?)" for user "(.*?)"')
def create_nova_project(step, name, user):
    step_assert(step).assert_true(utils.nova_cli.create_project(name, user))


@step(u'I remove nova project "(.*?)"')
def remove_nova_project(step, name):
    step_assert(step).assert_true(utils.nova_cli.remove_project(name))


@step(u'nova project "(.*?)" exists')
def nova_project_exists(step, project):
    step_assert(step).assert_true(utils.nova_cli.project_exists(project))

@step(u'nova project "(.*?)" does not exists')
def nova_project_exists(step, project):
    step_assert(step).assert_false(utils.nova_cli.project_exists(project))

@step(u'nova user "(.*?)" is the manager of the nova project "(.*?)"')
def nova_user_is_project_manager(step, user, project):
    step_assert(step).assert_true(utils.nova_cli.user_is_project_admin(user, project))


@step(u'I create nova network "(.*?)" with "(.*?)" nets, "(.*?)" IPs per network')
def create_nova_network(step, cidr, nets, ips):
    step_assert(step).assert_true(utils.nova_cli.create_network(cidr, nets, ips))


@step(u'I create nova network with the following parameters:')
def create_nova_network_by_params(step):
    flags = {}
    for data in step.hashes:
        flags[data['Parameter']] = data['Value']
    step_assert(step).assert_true(utils.nova_cli.create_network_via_flags(flags))


@step(u'nova network "(.*?)" exists')
def nova_network_exists(step, cidr):
    step_assert(step).assert_true(utils.nova_cli.network_exists(cidr))

@step(u'novarc for project "(.*?)", user "(.*?)" is available')
def novarc_is_available(step, project, user):
    utils.nova_cli.set_novarc(project, user, None, bunch_working_dir)
    step_assert(step).assert_true(utils.nova_cli.novarc_available())

@step(u'novarc for project "(.*?)", user "(.*?)", password "(.*?)" is available')
def novarc_is_available_ks(step, project, user, password):
    utils.nova_cli.set_novarc(project, user, password, bunch_working_dir)
    step_assert(step).assert_true(utils.nova_cli.novarc_available())


@step(u'VM image tarball is available at "(.*?)"')
def http_resource_is_availaable(step, url):
    step_assert(step).assert_true(utils.networking.http.probe(url))

@step(u'I download VM image tarball at "(.*?)" and unpack it')
def download_tarball_then_unpack(step, url):
    step_assert(step).assert_true(utils.networking.http.get(url, bunch_working_dir))
    file = os.path.join(bunch_working_dir, utils.networking.http.basename(url))
    step_assert(step).assert_true(utils.misc.extract_targz(file, bunch_working_dir))

@step(u'I download VM image tarball at "(.*?)"')
def download_tarball(step, url):
    step_assert(step).assert_true(utils.networking.http.get(url, bunch_working_dir))

@step(u'using glance I register VM image "(.*?)" for owner "(.*?)" using disk "(.*?)", ram "(.*?)", kernel "(.*?)"')
def register_all_images(step, name, owner, disk, ram, kernel):
    step_assert(step).assert_true(utils.glance_cli.vm_image_register(name, owner,
                                                                    os.path.join(bunch_working_dir,disk),
                                                                    os.path.join(bunch_working_dir,ram),
                                                                    os.path.join(bunch_working_dir, kernel)))

@step(u'using nova-manage I register VM image "(.*?)" for owner "(.*?)" using disk "(.*?)", ram "(.*?)", kernel "(.*?)"')
def register_all_images(step, name, owner, disk, ram, kernel):
    step_assert(step).assert_true(utils.nova_manage.vm_image_register(name, owner, os.path.join(bunch_working_dir, kernel),
                                                                    os.path.join(bunch_working_dir,ram),
                                                                    os.path.join(bunch_working_dir, kernel)))

@step(u'using nova-manage I register VM image "(.*?)" for owner "(.*?)" using disk "(.*?)"')
def register_all_images(step, name, owner, disk):
    step_assert(step).assert_true(utils.nova_manage.vm_image_register(name, owner, os.path.join(bunch_working_dir, disk), None, None))


@step(u'VM image "(.*?)" is registered')
def image_registered(step, name):
    step_assert(step).assert_true(utils.nova_cli.vm_image_registered(name))

@step(u'I generate keypair saving it to file "(.*?)"')
def gen_key_pair(step, file):
    key_path = os.path.join(bunch_working_dir,file)
    step_assert(step).assert_true(utils.misc.generate_ssh_keypair(key_path))

@step(u'I add keypair with name "(.*?)" from file "(.*?)"')
def add_keypair(step, name, file):
    key_path = os.path.join(bunch_working_dir,file)
    step_assert(step).assert_true(utils.nova_cli.add_keypair(name, key_path))

@step(u'I remove keypair with name "(.*?)"')
def delete_keypair(step, name):
    step_assert(step).assert_true(utils.nova_cli.delete_keypair(name))


@step(u'keypair with name "(.*?)" exists')
def keypair_exists(step, name):
    step_assert(step).assert_true(utils.nova_cli.keypair_exists(name))

@step(u'I see keypair "(.*?)" does not exists')
def keypair_exists(step, name):
    step_assert(step).assert_false(utils.nova_cli.keypair_exists(name))


@step(u'I start VM instance "(.*?)" using image "(.*?)",  flavor "(.*?)" and keypair "(.*?)"')
def start_vm_instance(step, name,image, flavor, keyname):
    id_image_list = utils.nova_cli.get_image_id_list(image)
    assert_equals(len(id_image_list), 1, "There are %s images with name %s: %s" % (len(id_image_list), image, str(id_image_list)))
    id_flavor_list = utils.nova_cli.get_flavor_id_list(flavor)
    assert_equals(len(id_flavor_list), 1, "There are %s flavors with name %s: %s" % (len(id_flavor_list), flavor, str(id_flavor_list)))
    image_id = id_image_list[0]
    flavor_id = id_flavor_list[0]
    assert_true(image_id != '', image_id)
    assert_true(flavor_id != '', flavor_id)
    step_assert(step).assert_true(utils.nova_cli.start_vm_instance(name, image_id, flavor_id, keyname))


@step(u'I start VM instance "(.*?)" using image "(.*?)",  flavor "(.*?)", keypair "(.*?)" in security groups "(.*?)"')
def start_vm_instance(step, name,image, flavor, keyname,sec_groups):
    id_image_list = utils.nova_cli.get_image_id_list(image)
    assert_equals(len(id_image_list), 1, "There are %s images with name %s: %s" % (len(id_image_list), name, str(id_image_list)))
    id_flavor_list = utils.nova_cli.get_flavor_id_list(flavor)
    assert_equals(len(id_flavor_list), 1, "There are %s flavors with name %s: %s" % (len(id_flavor_list), name, str(id_flavor_list)))
    image_id = id_image_list[0]
    flavor_id = id_flavor_list[0]
    assert_true(image_id != '', image_id)
    assert_true(flavor_id != '', flavor_id)
    step_assert(step).assert_true(utils.nova_cli.start_vm_instance(name, image_id, flavor_id, keyname, sec_groups))

@step(u'I start VM instance "(.*?)" using image "(.*?)", flavor "(.*?)"')
def start_vm_instance_no_keypair(step, name,image, flavor):
    id_image_list = utils.nova_cli.get_image_id_list(image)
    assert_equals(len(id_image_list), 1, "There are %s images with name %s: %s" % (len(id_image_list), name, str(id_image_list)))
    id_flavor_list = utils.nova_cli.get_flavor_id_list(flavor)
    assert_equals(len(id_flavor_list), 1, "There are %s flavors with name %s: %s" % (len(id_flavor_list), name, str(id_flavor_list)))
    image_id = id_image_list[0]
    flavor_id = id_flavor_list[0]
    assert_true(image_id != '', image_id)
    assert_true(flavor_id != '', flavor_id)
    step_assert(step).assert_true(utils.nova_cli.start_vm_instance(name, image_id, flavor_id))

@step(u'I can not start VM instance "(.*?)" using image "(.*?)", flavor "(.*?)"')
@onfailure(utils.debug.save.nova_conf)
def start_vm_instance_same_name(step, name,image, flavor):
    id_image_list = utils.nova_cli.get_image_id_list(image)
    assert_equals(len(id_image_list), 1, "There are %s images with name %s: %s" % (len(id_image_list), name, str(id_image_list)))
    id_flavor_list = utils.nova_cli.get_flavor_id_list(flavor)
    assert_equals(len(id_flavor_list), 1, "There are %s flavors with name %s: %s" % (len(id_flavor_list), name, str(id_flavor_list)))
    image_id = id_image_list[0]
    flavor_id = id_flavor_list[0]
    assert_true(image_id != '', image_id)
    assert_true(flavor_id != '', flavor_id)
    #"Instance with such name alredy exist in the project "
    step_assert(step).assert_false(utils.nova_cli.start_vm_instance(name, image_id, flavor_id))

@step(u'I start VM instance "(.*?)" using image "(.*?)",  flavor "(.*?)" and save auto-generated password')
def start_vm_instance_save_root_pwd(step, name,image, flavor):
    id_image_list = utils.nova_cli.get_image_id_list(image)
    assert_equals(len(id_image_list), 1, "There are %s images with name %s: %s" % (len(id_image_list), image, str(id_image_list)))
    id_flavor_list = utils.nova_cli.get_flavor_id_list(flavor)
    assert_equals(len(id_flavor_list), 1, "There are %s flavors with name %s: %s" % (len(id_flavor_list), flavor, str(id_flavor_list)))
    image_id = id_image_list[0]
    flavor_id = id_flavor_list[0]
    assert_true(image_id != '', image_id)
    assert_true(flavor_id != '', flavor_id)
    table = utils.nova_cli.start_vm_instance_return_output(name, image_id, flavor_id)
    assert_true(table is not None)
    passwords = table.select_values('Value', 'Property', 'adminPass')
    step_assert(step).assert_equals(len(passwords), 1, "there should be one and only one adminPass")
    world.saved_root_password = passwords[0]
    conf.log(conf.get_bash_log_file(),"store world.saved_root_password=%s" % world.saved_root_password)

@step(u'I stop VM instance "(.*?)"')
def stop_vm_instance(step, name):
    step_assert(step).assert_true(utils.nova_cli.stop_vm_instance(name))

@step(u'VM instance "(.*?)" is stopped within "(.*?)" seconds')
def wait_instance_stopped(step, name, timeout):
    step_assert(step).assert_true(utils.nova_cli.wait_instance_stopped(name, int(timeout)))


@step(u'I kill all processes:')
def kill_all_processes(step):
    for data in step.hashes:
        step_assert(step).assert_true(utils.misc.kill_process(data['Process']))

@step(u'VM instance "(.*?)" comes up within "(.*?)" seconds')
def wait_instance_comes_up_within(step, name, timeout):
    step_assert(step).assert_true(utils.nova_cli.wait_instance_comes_up(name, int(timeout)))

@step(u'VM instance "(.*?)" is pingable within "(.*?)" seconds')
@onfailure(utils.debug.save.nova_conf,
    utils.debug.save.log('nova/nova-compute.log'),
    utils.debug.save.log('nova/nova-network.log'),
    utils.debug.save.command_output('sudo ifconfig -a', 'diag_command.log'),
    utils.debug.save.command_output('sudo brctl show', 'diag_command.log'))
def vm_is_pingable(step, name, timeout):
    ip = utils.nova_cli.get_instance_ip(name)
    assert_true(ip != '', "Instance %s has no IP address" % name)
    step_assert(step).assert_true(utils.networking.icmp.probe(ip, int(timeout)))

@step(u'address "(.*?)" is pingable within "(.*?)" seconds')
def address_is_pingable(step, name, timeout):
    ip = world.floating[name]
    assert_true(ip != '', name)
    step_assert(step).assert_true(utils.networking.icmp.probe(ip, int(timeout)))

@step(u'I see that "(.*?)" port of VM instance "(.*?)" is open and serves "(.*?)" protocol within "(.*?)" seconds')
def check_port_protocol(step, port, name, protocol, timeout):
    ip = utils.nova_cli.get_instance_ip(name)
    assert_true(ip != '', name)
    step_assert(step).assert_true(utils.networking.nmap.open_port_serves_protocol(ip, port, protocol, timeout))


@step(u'I can log into VM "(.*?)" via SSH as "(.*?)" with key "(.*?)"')
@onfailure(utils.debug.save.nova_conf,
    utils.debug.save.log('nova/nova-compute.log'))
def check_can_log_via_ssh_with_external_key(step, name, user, key):
    ip = utils.nova_cli.get_instance_ip(name)
    assert_true(ip != '', name)
    key_path = os.path.join(bunch_working_dir,key)
    step_assert(step).assert_true(utils.ssh(ip, command="exit", user=user, key=key_path).successful())

@step(u'I can log into VM "(.*?)" via SSH as "(\w*?)" using saved password')
@onfailure(utils.debug.save.nova_conf,
    utils.debug.save.log('nova/nova-compute.log'))
def check_can_log_via_ssh_using_saved_pwd(step, name, user):
    ip = utils.nova_cli.get_instance_ip(name)
    assert_true(ip != '', name)
    assert_true(world.saved_root_password is not None)
    conf.log(conf.get_bash_log_file(),"load world.saved_root_password=%s" % world.saved_root_password)
    step_assert(step).assert_true(utils.ssh(ip, command="/bin/ls -l /", user=user, password=world.saved_root_password).successful())

@step(u'I create bridge "(.*)"')
def create_bridge(step, bridge_name):
    step_assert(step).assert_true(utils.networking.brctl.create_bridge(bridge_name))


@step('I add interface "(.*)" to the bridge "(.*)"')
def add_interface_to_bridge(step, interface, bridge):
    step_assert(step).assert_true(utils.networking.brctl.add_interface(bridge, interface))

@step('I configure interface "(.*)" assigning address "(.*)" and netmask "(.*)"')
def configure_ip_address_on_interface(step, interface, address, netmask):
    step_assert(step).assert_true(
        utils.networking.ifconfig.set(
            interface, '{address} netmask {netmask}'.format(address=address, netmask=netmask)))

@step('interface "(.*)" has address "(.*)"')
def interface_has_address(step, interface, address):
    step_assert(step).assert_true(
        utils.networking.ip.addr.show(interface).output_contains_pattern('inet(\s+){address}'.format(address=address)))


@step('interface "(.*)" exists')
def interface_exists(step, interface):
    step_assert(step).assert_true(utils.networking.ifconfig.interface_exists(interface))

@step('I delete bridge "(.*)"')
def delete_bridge(step, bridge):
    step_assert(step).assert_true(utils.networking.brctl.delete_bridge(bridge))


@step('interface does not "(.*)" exist')
def interface_does_not_exist(step, interface):
    step_assert(step).assert_false(utils.networking.ifconfig.interface_exists(interface))


@step(u'I create loop device "(.*?)" in file "(.*?)" with size "(.*?)" gigabytes')
def create_loop_device_in_file(step, source_dev, source_file, source_size):
    step_assert(step).assert_true(utils.misc.create_loop_dev(loop_dev=source_dev, loop_file=source_file, loop_size=source_size))

@step(u'I remove loop device "(.*?)"')
def remove_virtual_storage_device(step, source_dev):
    step_assert(step).assert_true(utils.misc.delete_loop_dev(loop_dev=source_dev))

@step(u'I see loop device "(.*?)" available')
def check_loop_device_available(step, source_dev):
    step_assert(step).assert_true(utils.misc.check_loop_dev_exist(loop_dev=source_dev))

@step(u'I see loop device "(.*?)" removed')
def check_loop_device_unavailable(step, source_dev):
    step_assert(step).assert_false(utils.misc.check_loop_dev_exist(loop_dev=source_dev))

@step(u'I create lvm group "(.*?)" on device "(.*?)"')
def create_lvm_group(step, lvm_group, source_dev):
    step_assert(step).assert_true(utils.misc.create_lvm(lvm_dev=source_dev,lvm_group=lvm_group))

@step(u'I remove lvm group "(.*?)" on device "(.*?)"')
def remove_lvm_group(step, lvm_group, source_dev):
    step_assert(step).assert_true(utils.misc.delete_lvm(lvm_dev=source_dev,lvm_group=lvm_group))

@step(u'I see lvm group "(.*?)" on device "(.*?)" available')
def check_lvm_group_available(step, lvm_group, source_dev):
    step_assert(step).assert_true(utils.misc.check_lvm_available(lvm_dev=source_dev,lvm_group=lvm_group))

@step(u'I see lvm group "(.*?)" on device "(.*?)" removed')
def check_lvm_group_unavailable(step, lvm_group, source_dev):
    step_assert(step).assert_false(utils.misc.check_lvm_available(lvm_dev=source_dev,lvm_group=lvm_group))

@step(u'I create volume "(.*?)" with size of "(.*?)" in zone "(.*?)"')
def create_volume(step, volume_name, volume_size, volume_zone):
    step_assert(step).assert_true(utils.euca_cli.volume_create(name=volume_name, size=volume_size, zone=volume_zone))

@step(u'I remove volume "(.*?)"')
def remove_volume(step, volume_name):
    step_assert(step).assert_true(utils.euca_cli.volume_delete(volume_name=volume_name))

@step(u'volume "(.*?)" comes up within "(.*?)" seconds')
def check_volume_comes_up(step, volume_name, timeout):
    step_assert(step).assert_true(utils.euca_cli.wait_volume_comes_up(volume_name=volume_name, timeout=timeout))

@step(u'I see volume "(.*?)" available')
def check_volume_available(step, volume_name):
    step_assert(step).assert_equals(utils.euca_cli.get_volume_status(volume_name=volume_name)['status'], 'available', 'Volume is not available')

@step(u'I see volume "(.*?)" removed')
def check_volume_removed(step, volume_name):
    step_assert(step).assert_true(utils.euca_cli.check_volume_deleted(volume_name=volume_name))

@step(u'I attach volume "(.*?)" to VM instance "(.*?)" as device "(.*?)"')
def attach_volume(step, volume_name, instance_name, volume_dev):
    step_assert(step).assert_true(utils.euca_cli.volume_attach(instance_name=instance_name, dev=volume_dev, volume_name=volume_name))

@step(u'I see volume "(.*?)" attached to VM instance "(.*?)"')
def check_volume_attached(step, volume_name, instance_name):
    step_assert(step).assert_true(utils.euca_cli.volume_attached_to_instance(instance_name=instance_name, volume_name=volume_name))

@step(u'I detach volume "(.*?)"')
def attach_volume(step, volume_name):
    step_assert(step).assert_true(utils.euca_cli.volume_detach(volume_name=volume_name))

@step(u'I login to VM "(.*?)" via SSH as "(.*?)" with key "(.*?)" and run commands:')
def run_commands_in_instance(step, vmname, user, key):
    ip = utils.nova_cli.get_instance_ip(vmname)
    assert_true(ip != '', vmname)
    key_path = os.path.join(bunch_working_dir,key)
    for data in step.hashes:
        if 'noFail' == data['Expected'].strip():
            step_assert(step).assert_true(utils.ssh(ip, command=data['Command'], user=user, key=key_path).successful())
        else:
            step_assert(step).assert_equals(utils.ssh(ip, command=data['Command'], user=user, key=key_path).output_text().strip(),data['Expected'].strip())

@step(u'I run commands:')
def run_commands(step):
    for data in step.hashes:
        if 'noFail' == data['Expected'].strip():
            step_assert(step).assert_true(utils.bash(data['Command']).successful())
        else:
            step_assert(step).assert_equals(utils.bash(data['Command']).output_text().strip(),data['Expected'].strip())


@step(u'commands are executed without errors')
def no_errors(step):
    pass

#####  KEYSTONE
@step(u'I init keystone db for IP "(.*?)", admin "(.*?)", password "(.*?)", project "(.*?)", token "(.*?)", region "(.*?)"')
def keystone_init_db(step, host, user, password, project, token, region):
    step_assert(step).assert_true(utils.keystone_manage.init_default(host, user, password, project, token, region))

@step(u'I setup keystone middleware')
def keystone_setup_middleware(step):
    step_assert(step).assert_true(utils.keystone.setup_middleware())

@step(u' I create keystone user "(.*?)" with password "(.*?)" in tenant "(.*?)"')
def keystone_create_user(step, user, password, tenant):
    step_assert(step).assert_true(utils.keystone_manage.create_user(user, password, tenant))

@step(u' I see keystone user "(.*?)" exist')
def keystone_user_exist(step, user):
    step_assert(step).assert_true(utils.keystone_manage.check_user_exist(user))

@step(u' I grant role "(.*?)" for keystone user "(.*?)"')
def keystone_grant_role(step, role, user):
    step_assert(step).assert_true(utils.keystone_manage.grant_role(role, user))

@step(u' I see role "(.*?)" granted for keystone user "(.*?)"')
def keystone_check_grant_role(step, role, user):
    step_assert(step).assert_true(utils.keystone_manage.check_role_granted(role, user))

@step(u' I create token "(.*?)" for keystone user "(.*?)" in tenant "(.*?)"')
def keystone_create_token(step, token, user, tenant):
    step_assert(step).assert_true(utils.keystone_manage.add_token(user, tenant, token))

@step(u' I see token "(.*?)" for keystone user "(.*?)" in tenant "(.*?)" exist')
def keystone_check_token_exist(step, token, user, tenant):
    step_assert(step).assert_true(utils.keystone_manage.check_token_exist(user, tenant,token ))




#####  BILLING
@step(u'for project "(.*?)", at least "(.*?)" instances and "(.*?)" images are billed')
def billed_objects(step, project, min_instances, min_images):
    step_assert(step).assert_true(utils.nova_cli.billed_objects(project, int(min_instances), int(min_images)))


#####  SECURITY GROUP
@step(u'I add security group "(.*?)"')
def add_security_group(step, group_name):
    step_assert(step).assert_true(utils.euca_cli.sgroup_add(group_name=group_name))

@step(u'I remove security group "(.*?)"')
def remove_security_group(step, group_name):
    step_assert(step).assert_true(utils.euca_cli.sgroup_delete(group_name=group_name))

@step(u'I see security group "(.*?)" exist')
def check_security_group_exist(step, group_name):
    step_assert(step).assert_true(utils.euca_cli.sgroup_check(group_name=group_name))

@step(u'I see security group "(.*?)" does not exist')
def check_security_group_not_exist(step, group_name):
    step_assert(step).assert_false(utils.euca_cli.sgroup_check(group_name=group_name))

@step(u'I add rule allow from group "(.*?)", protocol "(.*?)", host "(.*?)" to access port "(.*?)" in group "(.*?)"')
def add_security_group_rule(step,from_group, proto, src, port, dst_group):
    step_assert(step).assert_true(utils.euca_cli.sgroup_add_rule(dst_group=dst_group, src_group=from_group, src_proto=proto, src_host=src, dst_port=port))

@step(u'I remove rule allow from group "(.*?)", protocol "(.*?)", host "(.*?)" to access port "(.*?)" in group "(.*?)"')
def remove_security_group_rule(step,from_group, proto, src, port, dst_group):
    step_assert(step).assert_true(utils.euca_cli.sgroup_del_rule(dst_group=dst_group, src_group=from_group, src_proto=proto, src_host=src, dst_port=port))

@step(u'I see rule allow from group "(.*?)", protocol "(.*?)", host "(.*?)" to access port "(.*?)" in group "(.*?)" exist')
def check_security_group_rule_exist(step,from_group, proto, src, port, dst_group):
    step_assert(step).assert_true(utils.euca_cli.sgroup_check_rule(dst_group=dst_group, src_group=from_group, src_proto=proto, src_host=src, dst_port=port))

@step(u'I see rule allow from group "(.*?)", protocol "(.*?)", host "(.*?)" to access port "(.*?)" in group "(.*?)" does not exist')
def check_security_group_rule_not_exist(step,from_group, proto, src, port, dst_group):
    step_assert(step).assert_false(utils.euca_cli.sgroup_check_rule(dst_group=dst_group, src_group=from_group, src_proto=proto, src_host=src, dst_port=port))


#####  FLOATING IP
@step(u'I add pool of external IP addresses "(.*?)"')
def add_floating_pool(step, cidr):
    step_assert(step).assert_true(utils.nova_manage.floating_add_pool(cidr))

@step(u'I remove pool of external IP addresses "(.*?)"')
def remove_floating_pool(step, cidr):
    step_assert(step).assert_true(utils.nova_manage.floating_remove_pool(cidr))

@step(u'I see pool of external IP addresses "(.*?)" exist')
def check_floating_pool_exist(step, cidr):
    step_assert(step).assert_true(utils.nova_manage.floating_check_pool(cidr))

@step(u'I see pool of external IP addresses "(.*?)" does not exist')
def check_floating_pool_not_exist(step, cidr):
    step_assert(step).assert_false(utils.nova_manage.floating_check_pool(cidr))


@step(u'I allocate address "(.*?)"')
def allocate_floating_address(step, name):
    step_assert(step).assert_true(utils.nova_cli.floating_allocate(name))

@step(u'I de-allocate address "(.*?)"')
def deallocate_floating_address(step, name):
    step_assert(step).assert_true(utils.nova_cli.floating_deallocate(name))

@step(u'I see address "(.*?)" allocated')
def floating_check_address_allocated(step, name):
    step_assert(step).assert_true(utils.nova_cli.floating_check_allocated(name))

@step(u'I see address "(.*?)" not allocated')
def floating_check_address_not_allocated(step, name):
    step_assert(step).assert_false(utils.nova_cli.floating_check_allocated(name))

@step(u'I associate address "(.*?)" with instance "(.*?)"')
def associate_floating_address(step, address,instance):
    step_assert(step).assert_true(utils.nova_cli.floating_associate(address, instance))

@step(u'I de-associate address "(.*?)" from instance "(.*?)"')
def deassociate_floating_address(step, address,instance):
    step_assert(step).assert_true(utils.nova_cli.floating_deassociate(address, instance))

@step(u'I see address "(.*?)" associated with instance "(.*?)"')
def check_address_associated(step, address,instance):
    step_assert(step).assert_true(utils.nova_cli.floating_check_associated(address, instance))

@step(u'I see address "(.*?)" not associated with instance "(.*?)"')
def check_address_associated(step, address,instance):
    step_assert(step).assert_false(utils.nova_cli.floating_check_associated(address, instance))


