import os
import yaml
import time

#bash_log_file
#env_dir_path

def get_bash_log_file():
    global bash_log_file
    return bash_log_file

def init(dir_path):
    print dir_path
    global bash_log_file, env_dir_path
    env_dir_path = dir_path
    bash_log_file = os.path.join(env_dir_path, "bash.log")


def load_yaml_config(filename):
    with open(filename, 'r') as config_file:
        config = yaml.load(config_file)
        return config


def log(logfile, message):
    with open(logfile, 'a+b') as file:
        file.write('%s: %s\n' % (time.ctime(), message))


def bash_log(cmd, status, text):
    log(get_bash_log_file(), "[COMMAND] " + cmd)
    log(get_bash_log_file(), "[RETCODE] %s" % status)
    log(get_bash_log_file(), "[OUTPUT]\n %s" % text)


def get_current_module_path(module_file):
    return os.path.dirname(os.path.abspath(module_file))

