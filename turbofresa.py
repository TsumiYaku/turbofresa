#!/usr/bin/env python3
"""
    T.U.R.B.O.F.R.E.S.A
    Turboaggeggio Utile alla Rimorzione di Byte Obrobriosi e di abominevoli
    File da dischi rigidi Riciclati ed altri Elettronici Sistemi di
    Archiviazione di dati.
    Contributors:
        Hyd3L
        e-caste

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os, sys
import logging  # TODO: Add log messages
from multiprocessing import Process
import subprocess as sp
import argparse
import smartctl_parser
from pytarallo import Tarallo, Errors, Item
from dotenv import load_dotenv

__version__ = '1.3'

# Run parameters
quiet = None
simulate = None
tarallo_instance = None


def ask_confirm(disks: list):
    print("\nThe following disks are going to be wiped:")

    for d in disks:
        print("- /dev/" + d['mount_point'])

    while True:
        user_response = input("\nAre you 100% sure of what you're about to do? [N/y] ")
        if user_response.lower() == 'y':
            break
        elif user_response.lower() == 'n':
            exit(0)
        else:
            print("Unrecognized response... Asking again nicely.")


def ignore_sys_disks() -> list:
    """
    Checks which disks have system partitions in them and asks if the user wishes to add
    other disks to ignored
    :return: Full list of ignored disks (system + user specified)
    """

    critical = [
        "/boot",
        "/home",
        "/etc",
        "/var",
        "/lib",
        "/root",
        "/opt",
        "/usr",
        "/var"
    ]

    output = sp.check_output(["sudo", "-S", "df", "--output=source,target"]).decode(sys.stdout.encoding)

    result = []
    for line in output.splitlines():
        source = line.split()[0]
        target = line.split()[1]

        if "/dev/sd" in source:
            for partition in critical:
                if partition in target or target == "/":
                    disk = source.split("/dev/")[1]
                    disk = ''.join(c for c in disk if not c.isdigit())
                    if disk not in result:
                        print(f'The partition "{target}" has been detected in "{source}", '
                              f'the disk "{disk}" will be ignored')
                        result.append(disk)
                    break

    return result


def ignore_user_disks() -> list:
    user_response = input("Do you wish to add more disks to ignore from wiping? [y/N] ")
    if user_response.lower() == 'y':
        user_ignored = input("Insert disks to ignore separated by comma (sda,sdb,loop0,etc...): ")
        if user_ignored:
            return user_ignored.replace(" ", "").split(",")


class Task(Process):
    """
    Disk cleaning process
    """
    def __init__(self, disk):
        """
        :param disk: Disk object
        """
        super().__init__()
        self.disk = disk

    def run(self):
        """
        This is the crucial part of the program.
        Here badblocks writes a stream of 0x00 bytes on the hard drive.
        After the writing process, it reads every blocks to ensure that they are actually 0x00 bytes.
        Bad blocks are eventually written in a txt file named as HDDXXX or sdX in case of failures
        while retrieving the HDD code from T.A.R.A.L.L.O.
        If this file is empty, then the disk is good to go, otherwise it'll be kept
        and the broken hard drive is reported into the log file and informations
        are written to the T.A.R.A.L.L.O. database.
        """
        code = self.disk['code'][0]
        mount_point = self.disk['mount_point']
        filename = 'badblocks_error_logs/' + code + '.txt'
        process = sp.Popen(['sudo', 'badblocks', '-w', '-t', '0x00', '-o', filename, "/dev/"+mount_point])
        process.communicate()
        exit_code = process.returncode

        global quiet
        if not quiet:
            print("Ended cleaning /dev/" + mount_point)

        # result = os.popen('cat %s' % self.disk.code).read()
        # if result == "":
        if exit_code == 0:
            os.remove(filename)
            return True
        else:
            # TODO: Write on tarallo that the hard drive is broken
            # Write it in the turbofresa log file as well
            global tarallo_instance
            self.disk['features']['smart-data'] = smartctl_parser.SMART.fail
            add_to_tarallo_broken(tarallo_instance, self.disk['features'])
            return False


def add_to_tarallo(instance: Tarallo.Tarallo, disk: dict) -> bool:
    """
    Adds disk to Tarallo database
    :param instance: Tarallo instance where to add the disk
    :param disk: disk to add to the database
    :return: True if added successfully or it was already present,
        False if there were multiple instances of it in the database
    """

    print("\nSearching the T.A.R.A.L.L.O. databse for disk with serial number {}".format(disk['sn']))
    disk_code = instance.get_codes_by_feature('sn', disk['sn'])

    if len(disk_code) > 1:
        print("Multiple disks in the database corresponding to the serial number: " + disk['sn'])
        print("Won't proceed until conflict is solved")
        return False
    elif len(disk_code) == 1:
        print(f"Disk with serial number {disk['sn']} already present in the database"
              f"with the code {disk_code[0]}")
        item = instance.get_item(disk_code[0])
        for key, value in item.features.items():
            if key == 'smart-data' or key == 'smart-data-long':
                continue
            if value != disk[key]:
                print("There's a conflict in the database for this disk")
                print("Won't proceed until conflict is solved")
                return False
        print("The entry doesn't conflict with the current disk, proceeding anyway")
        return True
    elif len(disk_code) == 0:
        print("No corresponding disk in the database")

    print("Adding disk to the database")
    item = Item.Item()
    item.features = disk
    item.location = 'Polito'  # TODO: maybe it can be set from config or a better default should be picked

    try:
        instance.add_item(item=item)
        print("Item inserted successfully")
    except Errors.ValidationError:
        print("Item not inserted")
        response = instance.response
        print("HTTP status code:", response.status_code, "\n" + response.json()['message'])
        return False

    print("Successfully added the disk")
    print("Disk code on the Database: " + instance.get_codes_by_feature('sn', disk['sn'])[0])
    return True


def add_to_tarallo_broken(instance: Tarallo.Tarallo, disk: dict) -> bool:
    if disk['smart-data'] != smartctl_parser.SMART.fail.value:
        print("Not a broken disk")
        return False

    if add_to_tarallo(instance, disk) is False:
        print("Failed to update informations")
        return False

    disk_code = instance.get_codes_by_feature('sn', disk['sn'])
    try:
        instance.update_features(disk_code[0], disk)
    except Errors.ValidationError:
        print("Failed to update informations")
        response = instance.response
        print("HTTP status code:", response.status_code, "\n" + response.json()['message'])
        return False

    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Automatically drill every single connected hard drive.')
    parser.add_argument('-s', '--shutdown', action='store_true', help='Shutdown the machine when everything is done.')
    parser.add_argument('-q', '--quiet', action='store_true', help='Run in background and suppress stdout.')
    parser.add_argument('-d', '--dry', action='store_true', help='Launch simulation.')
    parser.add_argument('--usb', action='store_true', help='Allow cleaning of usb drives (DEBUG ONLY!!!)')
    parser.add_argument('--version', '-V', action='version', version='%(prog)s v.' + __version__)
    parser.set_defaults(shutdown=False)
    parser.set_defaults(quiet=False)
    parser.set_defaults(dry=False)
    parser.set_defaults(usb=False)
    args = parser.parse_args()

    quiet = args.quiet
    simulate = args.dry

    print("The program will completely wipe any disk outside system ones connected to the current machine")

    # Preliminary operations
    if not quiet:
        print('\n\n===> Checking system disks')
    ignored = ignore_sys_disks()
    ignored = ignored + ignore_user_disks()

    # Disks parsing
    if not quiet:
        print("\n\n===> Detecting connected hard drives.")
    disks = smartctl_parser.parse_disks(interactive=not quiet, usbdebug=args.usb, ignore=ignored)
    if len(disks) == 0:
        print("No valid device detected.")
        exit(0)
    tasks = []
    ask_confirm(disks)

    # Tarallo connection
    if not quiet:
        print('\n\n===> Connecting to T.A.R.A.L.L.O. database')
    load_dotenv()
    try:
        tarallo_instance = Tarallo.Tarallo(os.getenv("TARALLO_URL"), os.getenv("TARALLO_TOKEN"))
    except:
        print('Failed to connect to the database')
        exit(1)
    print('Successfully connected to the database')

    # Adding disks to clean in queue and adding them to Tarallo if not present
    if not quiet:
        print('\n\n===> Adding disks to T.A.R.A.L.L.O.')

    for d in disks:
        disk = d['features']

        if add_to_tarallo(tarallo_instance, disk) is False:
            print("Something went wrong with Disk addition to database, skipping to the next one")
            continue

        d['code'] = tarallo_instance.get_codes_by_feature('sn', disk['sn'])
        tasks.append(Task(d))

    # Time to TURBOFRESA
    if not quiet:
        print("\n\n===> Cleaning disks")

    if not simulate:
        if 'badblocks_error_logs' not in os.listdir(os.getcwd()):
            os.mkdir('badblocks_error_logs')

    for t in tasks:
        if not quiet:
            print("Started cleaning /dev/" + t.disk['mount_point'])
        if not simulate:
            t.start()

    for t in tasks:
        if not simulate:
            t.join()
        else:
            if not quiet:
                print("Ended cleaning /dev/" + t.disk['mount_point'])

    if simulate:
        for d in disks:
            tarallo_instance.remove_item(d['code'][0])

    if args.shutdown is True:
        if not simulate:
            sp.run(['sudo', 'shutdown'])
        else:
            if not quiet:
                print("System halted by the user.")
    if not quiet:
        print("Done.")
    exit(0)