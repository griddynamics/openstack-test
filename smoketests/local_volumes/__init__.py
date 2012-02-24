from datetime import datetime
from lettuce import step, world
from nose.tools import assert_equals, assert_true, assert_false
from time import sleep
import re
import os
import lettuce_bunch.special
from openstack_core_test import utils
from openstack_core_test.utils import onfailure, debug, conf
from lettuce_bunch.special import get_current_bunch_dir

get_current_bunch_dir()


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

@step(u'yum repository with id "(.*?)" is configured')
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

@step(u'I set MySQL root password to "(.*)"')
def setup_db_password(step, admin_pwd):
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

    
@step(u'the following flags in file "(.*?)" are set to:')
def verify_flag_file(step,flag_file):
    flags = [(flag['Name'],flag['Value']) for flag in step.hashes ]
    step_assert(step).assert_true(utils.FlagFile(flag_file).verify(flags))

@step(u'I create nova admin user "(.*?)"')
def create_nova_admin(step, username):
    step_assert(step).assert_true(utils.nova_cli.create_admin(username))


@step(u'nova user "(.*?)" exists')
def nova_user_exists(step, user):
    step_assert(step).assert_true(utils.nova_cli.user_exists(user))

@step(u'I create nova project "(.*?)" for user "(.*?)"')
def create_nova_project(step, name, user):
    step_assert(step).assert_true(utils.nova_cli.create_project(name, user))


@step(u'nova project "(.*?)" exists')
def nova_project_exists(step, project):
    step_assert(step).assert_true(utils.nova_cli.project_exists(project))

@step(u'nova user "(.*?)" is the manager of the nova project "(.*?)"')
def nova_user_is_project_manager(step, user, project):
    step_assert(step).assert_true(utils.nova_cli.user_is_project_admin(user, project))


@step(u'I create nova network "(.*?)" with "(.*?)" nets, "(.*?)" IPs per network')
def create_nova_network(step, cidr, nets, ips):
    step_assert(step).assert_true(utils.nova_cli.create_network(cidr, nets, ips))


@step(u'nova network "(.*?)" exists')
def nova_network_exists(step, cidr):
    step_assert(step).assert_true(utils.nova_cli.network_exists(cidr))


@step(u'novarc for project "(.*?)", user "(.*?)" is available')
def novarc_is_available(step, project, user):
    utils.nova_cli.set_novarc(project, user, bunch_working_dir)
    step_assert(step).assert_true(utils.nova_cli.novarc_available())


@step(u'VM image tarball is available at "(.*?)"')
def http_resource_is_availaable(step, url):
    step_assert(step).assert_true(utils.networking.http.probe(url))

@step(u'I download VM image tarball at "(.*?)" and unpack it')
def download_tarball_then_unpack(step, url):
    step_assert(step).assert_true(utils.networking.http.get(url, bunch_working_dir))
    file = os.path.join(bunch_working_dir, utils.networking.http.basename(url))
    step_assert(step).assert_true(utils.misc.extract_targz(file, bunch_working_dir))

@step(u'I register VM image "(.*?)" for owner "(.*?)" using disk "(.*?)", ram "(.*?)", kernel "(.*?)"')
def register_all_images(step, name, owner, disk, ram, kernel):
    step_assert(step).assert_true(utils.nova_cli.vm_image_register(name, owner,
                                                                    os.path.join(bunch_working_dir,disk),
                                                                    os.path.join(bunch_working_dir,ram),
                                                                    os.path.join(bunch_working_dir, kernel)))


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

@step(u'keypair with name "(.*?)" exists')
def keypair_exists(step, name):
    step_assert(step).assert_true(utils.nova_cli.keypair_exists(name))

@step(u'I start VM instance "(.*?)" using image "(.*?)",  flavor "(.*?)" and keypair "(.*?)"')
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

@step(u'I start VM instance "(.*?)" using image "(.*?)",  flavor "(.*?)" and save auto-generated password')
def start_vm_instance_save_root_pwd(step, name,image, flavor):
    id_image_list = utils.nova_cli.get_image_id_list(image)
    assert_equals(len(id_image_list), 1, "There are %s images with name %s: %s" % (len(id_image_list), name, str(id_image_list)))
    id_flavor_list = utils.nova_cli.get_flavor_id_list(flavor)
    assert_equals(len(id_flavor_list), 1, "There are %s flavors with name %s: %s" % (len(id_flavor_list), name, str(id_flavor_list)))
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

@step(u'I kill all processes:')
def kill_all_processes(step):
    for data in step.hashes:
        step_assert(step).assert_true(utils.misc.kill_process(data['Process']))

@step(u'I suspend VM instance "(.*?)"')
def suspend_instance(step, vm_name):
    instance_id = utils.nova_cli.get_instance_id(vm_name)
    step_assert(step).assert_true(utils.nova_cli.exec_novaclient_cmd('suspend %s' % instance_id))

@step(u'I resume VM instance "(.*?)"')
def resume_instance(step, vm_name):
    instance_id = utils.nova_cli.get_instance_id(vm_name)
    step_assert(step).assert_true(utils.nova_cli.exec_novaclient_cmd('resume %s' % instance_id))

@step(u'VM instance "(.*?)" is suspended within "(.*?)" seconds')
def wait_instance_suspended(step, name, timeout):
    step_assert(step).assert_true(utils.nova_cli.wait_instance_state(name, 'SUSPENDED', int(timeout)))

@step(u'VM instance "(.*?)" comes up within "(.*?)" seconds')
def wait_instance_comes_up_within(step, name, timeout):
    step_assert(step).assert_true(utils.nova_cli.wait_instance_comes_up(name, int(timeout)))

@step(u'VM instance "(.*?)" is pingable within "(.*?)" seconds')
@onfailure(utils.debug.save.log('nova/nova-compute.log'))
def vm_is_pingable(step, name, timeout):
    ip = utils.nova_cli.get_instance_ip(name)
    assert_true(ip != '', name)
    step_assert(step).assert_true(utils.networking.icmp.probe(ip, int(timeout)))

@step(u'I see that "(.*?)" port of VM instance "(.*?)" is open and serves "(.*?)" protocol within "(.*?)" seconds')
def check_port_protocol(step, port, name, protocol, timeout):
    ip = utils.nova_cli.get_instance_ip(name)
    assert_true(ip != '', name)
    step_assert(step).assert_true(utils.networking.nmap.open_port_serves_protocol(ip, port, protocol, timeout))


@step(u'I can log into VM "(.*?)" via SSH as "(.*?)" with key "(.*?)"')
def check_can_log_via_ssh_with_external_key(step, name, user, key):
    ip = utils.nova_cli.get_instance_ip(name)
    assert_true(ip != '', name)
    key_path = os.path.join(bunch_working_dir,key)
    step_assert(step).assert_true(utils.ssh(ip, command="exit", user=user, key=key_path).successful())

@step(u'I can log into VM "(.*?)" via SSH as "(\w*?)" using saved password')
def check_can_log_via_ssh_using_saved_pwd(step, name, user):
    ip = utils.nova_cli.get_instance_ip(name)
    assert_true(ip != '', name)
    assert_true(world.saved_root_password is not None)
    conf.log(conf.get_bash_log_file(),"load world.saved_root_password=%s" % world.saved_root_password)
    step_assert(step).assert_true(utils.ssh(ip, command="/bin/ls -l /", user=user, password=world.saved_root_password).successful())


def get_expect_before(expect_output):
    return re.search('(\d+)', expect_output, flags=re.M).groups()[0]

def ssh_command(step, vm_name, user, command):
    ip = utils.nova_cli.get_instance_ip(vm_name)
    step_assert(step).assert_true(ip != '')
    step_assert(step).assert_true(world.saved_root_password is not None)
    conf.log(conf.get_bash_log_file(),"load world.saved_root_password=%s" % world.saved_root_password)
    return utils.ssh(ip,
        command=command,
        user=user,
        password=world.saved_root_password)

@step(u'I create volume for "(.*)" with size "(.*)" as device "(.*)"')
@onfailure(debug.save.log('nova/nova-compute.log'))
def create_clean_volume(step, vm_name, size, device):
    instance_id = utils.nova_cli.get_instance_id(vm_name)
    step_assert(step).assert_true(utils.nova_cli.exec_nova2ools_cmd('create --vm %s '\
                                                                    '--size %s'\
                                                                    ' --device %s' %
                                                                    (instance_id, size, device)))

@step(u'device "(.*)" is attached to "(.*)" in "(.*)" seconds')
@onfailure(debug.save.log('nova/nova-compute.log'))
def volume_is_attached(step, device, vm_name, timeout):
    instance_id = utils.nova_cli.get_instance_id(vm_name)
    volume_attached_to = None
    volume_status = None
    start_time = datetime.now()
    while(datetime.now() - start_time).seconds < int(timeout):
        volumes = utils.nova_cli.get_local_volumes('{instance_id} {device} {status}', 
                                                   ['Instance_Id', 'Device', 'Status'])
        candidates = volumes.select(['Status'], 
                                       lambda x: x['Instance_Id'] == instance_id and 
                                       x['Device'] == device)
        
        if len(candidates) == 1:
            status = candidates[0][0]
            if status == 'in-use':
                return True

    raise RuntimeError('Failed to attach volume:  Status=%s, Attached to=%s' % (volume_status, volume_attached_to))

@step(u'device "(.*)" exists in VM "(.*)" when I SSH as "(.*)" using saved password')
@onfailure(debug.save.log('nova/nova-compute.log'))
def check_device_exists(step, device, vm_name, user):
    command = ssh_command(step, vm_name, user, "/usr/bin/test -b %s" % device)
    step_assert(step).assert_true(command.successful())

@step(u'device "(.*)" doesn\'t exists in VM "(.*)" when I SSH as "(.*)" using saved password')
@onfailure(debug.save.log('nova/nova-compute.log'))
def check_device_does_not_exists(step, device, vm_name, user):
    command = ssh_command(step, vm_name, user, "/usr/bin/test ! -e %s" % device)
    step_assert(step).assert_true(command.successful())

@step(u'I can\'t create volume for "(.*)" with size "(.*)" as device "(.*)"')
@onfailure(debug.save.log('nova/nova-compute.log'))
def cant_create_volume(step, vm_name, size, device):
    instance_id = utils.nova_cli.get_instance_id(vm_name)
    step_assert(step).assert_false(utils.nova_cli.exec_nova2ools_cmd('create --vm %s '\
                                                                     ' --size %s'\
                                                                     ' --device %s' % (instance_id,
        size, device)))

@step(u'I create snapshot from device "(.*)" of "(.*)" with name "(.*)"')
@onfailure(debug.save.log('nova/nova-compute.log'))
def create_snapshot(step, device, vm_name, snapshot_name):
    volume_id = utils.nova_cli.get_local_volume_id(device, vm_name)
    step_assert(step).assert_true(
        utils.nova_cli.exec_nova2ools_cmd('snapshot --id %s --name %s' % (volume_id, snapshot_name))
    )

@step(u'snapshot "(.*)" is active within "(.*)" seconds')
@onfailure(debug.save.log('nova/nova-compute.log'))
def snapshot_is_ok(step, name, timeout):
    snapshot_id = utils.nova_cli.get_image_id_list(name)[0]
    start_time = datetime.now()
    while(datetime.now() - start_time).seconds < int(timeout):
        status = utils.nova_cli.get_novaclient_command_out(
            "image-list|grep %s| awk -F\| '{print $4}'" % snapshot_id)
        if status.strip() == 'ACTIVE':
            return True

    raise RuntimeError("%s:\nSnapshot is not active within %s seconds" % (step.sentence, timeout))

@step(u'I reboot VM instance "(.*)"')
@onfailure(debug.save.log('nova/nova-compute.log'))
def reboot_vm(step, vm_name):
    instance_id = utils.nova_cli.get_instance_id(vm_name)
    step_assert(step).assert_true(
        utils.nova_cli.exec_novaclient_cmd('reboot %s' % instance_id)
    )

@step(u'I create volume for "(.*)" from "(.*)" as device "(.*)"')
@onfailure(debug.save.log('nova/nova-compute.log'))
def create_volume_from_snapshot(step, vm_name, snapshot_name, device):
    instance_id = utils.nova_cli.get_instance_id(vm_name)
    snapshot_id = utils.nova_cli.get_image_id_list(snapshot_name)[0]
    step_assert(step).assert_true(
        utils.nova_cli.exec_nova2ools_cmd('create --vm %s '\
                                          ' --snapshot %s'\
                                          ' --device %s' % (instance_id,
            snapshot_id, device)
        )
    )

@step(u'I create volume with resizing for "(.*)" from "(.*)" with size "(.*)" as device "(.*)"')
@onfailure(debug.save.log('nova/nova-compute.log'))
def create_volume_from_snapshot_with_size(step, vm_name, snapshot_name, size, device):
    instance_id = utils.nova_cli.get_instance_id(vm_name)
    snapshot_id = utils.nova_cli.get_image_id_list(snapshot_name)[0]
    step_assert(step).assert_true(
        utils.nova_cli.exec_nova2ools_cmd('create --vm %s '\
                                          ' --snapshot %s'\
                                          ' --size %s --device %s' % (instance_id,
            snapshot_id, size, device)
        )
    )

@step(u'I resize device "(.*)" on "(.*)" to "(.*)"')
@onfailure(debug.save.log('nova/nova-compute.log'))
def resize_volume(step, device, vm_name, size):
    volume_id = utils.nova_cli.get_local_volume_id(device, vm_name)
    step_assert(step).assert_true(volume_id)
    step_assert(step).assert_true(utils.nova_cli.exec_nova2ools_cmd(
        'resize --id %s --size %s' % (volume_id, size))
    )

@step(u'device "(.*)" on "(.*)" is resized within "(.*)" seconds')
@onfailure(debug.save.log('nova/nova-compute.log'))
def volume_is_resized(step, device, vm_name, timeout):
    start_time = datetime.now()
    volume_id = utils.nova_cli.get_local_volume_id(device, vm_name)
    volume_name = "volume-%0.8x" % int(volume_id)
    while(datetime.now() - start_time).seconds < int(timeout):
        if utils.bash("cat /var/log/nova/nova-compute.log|grep 'Resize of volume %s is finished'" % volume_name).successful():
            return True
        sleep(1)
    raise RuntimeError("%s:\nVolume %s isn't resized within %s seconds" % (step.sentence, volume_name, timeout))

@step(u'size of device "(.*)" on "(.*)" is equal to "(.*)" within "(.*)" seconds')
@onfailure(debug.save.log('nova/nova-compute.log'))
def check_size_volume(step, device, vm_name, size, timeout):
    start_time = datetime.now()
    volume_size = None
    volume_id = utils.nova_cli.get_local_volume_id(device, vm_name)
    while(datetime.now() - start_time).seconds < int(timeout):
        volumes = utils.nova_cli.get_local_volumes("{id} {size}", ("Id", "Size"))
        volume_size = volumes.select_values('Size', 'Id', volume_id)[0]
        if volume_size == size:
            return True
    raise RuntimeError("%s:\nSize mismatched within %s seconds. Expected size: %s, real size: %s" %
                       (step.sentence, timeout, size, volume_size))

@step(u'device "(.*)" have size "(.*)" in VM "(.*)" when I SSH as "(.*)" using saved password within "(.*)" seconds')
@onfailure(debug.save.log('nova/nova-compute.log'))
def check_size(step, device, size, vm_name, user, timeout):
    start_time = datetime.now()
    internal_size = None
    while(datetime.now() - start_time).seconds < int(timeout):
        expect_output = ssh_command(step, vm_name, user, '/sbin/blockdev --getsize64 %s' % device).output_text().strip()
        internal_size = get_expect_before(expect_output)
        if internal_size == size:
            return True
    raise RuntimeError("%s:\nSize mismatched within %s seconds. Expected size: %s, real size: %s" %
                       (internal_size, timeout, size, internal_size))

@step(u'I delete device "(.*)" on "(.*)"')
@onfailure(debug.save.log('nova/nova-compute.log'))
def delete_volume(step, device, vm_name):
    volume_id = utils.nova_cli.get_local_volume_id(device, vm_name)
    step_assert(step).assert_true(volume_id)
    step_assert(step).assert_true(utils.nova_cli.exec_nova2ools_cmd('delete --id %s' % volume_id))

@step(u'device "(.*)" on "(.*)" is deleted within "(.*)" seconds')
@onfailure(debug.save.log('nova/nova-compute.log'))
def volume_is_deleted(step, device, vm_name, timeout):
    start_time = datetime.now()
    while(datetime.now() - start_time).seconds < int(timeout):
        volume_id = utils.nova_cli.get_local_volume_id(device, vm_name)
        if not volume_id:
            return True
    step_assert(step).assert_false(utils.nova_cli.get_local_volume_id(device, vm_name))

@step(u'I terminate "(.*)"')
@onfailure(debug.save.log('nova/nova-compute.log'))
def terminate_instance(step, vm_name):
    instance_id = utils.nova_cli.get_instance_id(vm_name)
    step_assert(step).assert_true(utils.nova_cli.terminate_instance(instance_id))

@step(u'"(.*)" is terminated within "(.*)" seconds')
@onfailure(debug.save.log('nova/nova-compute.log'))
def instance_is_terminated(step, vm_name, timeout):
    start_time = datetime.now()
    while(datetime.now() - start_time).seconds < int(timeout):
        instances = utils.ascii_table(utils.nova_cli.get_novaclient_command_out('list'))
        if not instances.select_values('ID', 'Name', vm_name):
            return True
    raise RuntimeError("%s:\nVM is not terminated" % step.sentence)

@step(u'I record volumes for "(.*)"')
@onfailure(debug.save.log('nova/nova-compute.log'))
def record_volumes(step, vm_name):
    instance_id = utils.nova_cli.get_instance_id(vm_name)
    step_assert(step).assert_true(instance_id)
    volumes = utils.nova_cli.get_local_volumes()
    world.volumes = volumes.select_values('Id', 'Instance_Id', instance_id)

@step(u'recorded volumes are deleted')
@onfailure(debug.save.log('nova/nova-compute.log'))
def volumes_are_deleted(step):
    if hasattr(world, "volumes"):
        try:
            volumes = utils.nova_cli.get_local_volumes()
            for id in world.volumes:
                step_assert(step).assert_false(volumes.select_values('Id', 'Id', id))
        finally:
            world.volumes = None

#noinspection PyUnusedLocal
@step(u'I record logical volumes in "(.*)"')
def record_lvm_volumes(step, vg_name):
    table = utils.ascii_table(utils.bash("sudo lvs|sed 's/Origin .* Convert//'| sed 's/  */\|/g'").output_text())
    world.lvm_volumes = table.select_values('LV', 'VG', vg_name)

@step(u'I cleanup logical volumes for "(.*)"')
def cleanup_lvm_volumes(step, vg_name):
    step_assert(step).assert_true(world.lvm_volumes)
    table = utils.ascii_table(utils.bash("sudo lvs|sed 's/Origin .* Convert//'| sed 's/  */\|/g'").output_text())
    all_volumes = table.select_values('LV', 'VG', vg_name)
    volumes_to_clean  = set(all_volumes) - set(world.lvm_volumes)
    for volume in volumes_to_clean:
        step_assert(step).assert_true(utils.bash('sudo lvremove -f %s/%s' % (vg_name, volume)))

