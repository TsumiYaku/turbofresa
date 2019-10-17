#!/usr/bin/env python3
"""
    T.U.R.B.O.F.R.E.S.A
    Turboaggeggio Utile alla Rimorzione di Byte Obrobriosi e di abominevoli
    File da dischi rigidi Riciclati ed altri Elettronici Sistemi di
    Archiviazione di dati.
    Copyright (C) 2018  Hyd3L

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

import os
import json
import logging  # TODO: Add log messages
import requests
from multiprocessing import Process
import subprocess as sp
import argparse
import pytarallo

__version__ = '1.3'

# Run parameters
quiet = None
simulate = None


def ask_confirm():
    """
    Asks the user if (s)he is sure of what (s)he's doing.
    """
    while True:
        user_response = input("Are you 100% sure of what you're about to do? [N/y] ")
        if user_response.lower() == 'y':
            break
        else:
            print("Unrecognized response... Asking again nicely.")


def tarallo_login() -> bool:
    """
    Checks if turbofresa is already logged in
    :return: True if logged or False if sth went wrong
    """
    try:
        whoami = requests.get('tarallo_link' + '/v1/session')

        if whoami.status_code == 200:
            return True

        if whoami.status_code == 403:
            body = dict()
            body['username'] = None  # Retrieve this from the config file
            body['password'] = None  # Retrieve this from the config file
            headers = {'Content-Type': 'application/json'}
            res = requests.post('tarallo_link' + '/v1/session', data=json.dumps(body), headers=headers)

            if res.status_code == 200:
                global tarallo_cookie
                tarallo_cookie = res.cookies
                return True
            else:
                return False
    except requests.exceptions.ConnectionError:
        if not simulate:
            # Write stuff to the log file
            pass
        else:
            if not quiet:
                print("Failed connection with T.A.R.A.L.L.O. Skipping retrieving HDD codes")


def detect_disks() -> list:
    """
    Detects the hard drives connected to the machine
    :return: a list like ['/dev/sdb', '/dev/sdc'] entries
    """
    #root = os.popen('df | grep /dev/sd | cut -b -8').read().split('\n')[0]
    hard_drives = []
    
    lsblk = json.loads(sp.check_output(['lsblk', "-J", "-o", "NAME,SERIAL,TYPE,WWN,MOUNTPOINT"]).decode('utf-8'))['blockdevices']
    #looking for hard drives with no mount points 
    ok_disks=[]
    for d in lsblk:
        ok = True
        if d["mountpoint"] is not None:
            ok=False        
        if("children" in d):      
            for child in d["children"]:
                if child["mountpoint"] is not None:
                    ok = False
                    break
        if ok is True:
            ok_disks.append(d["name"])
    #exclude anything that is not an hard drive
    disks=json.loads(sp.check_output(['lsblk', "-J", "-I 8", "-d", "-o", "NAME,SERIAL,TYPE,WWN"]).decode('utf-8'))['blockdevices']
    for dev in disks:
        disco={'name':'null', 'serial':'null', 'type':'null','wwn':'null'}
        if dev["name"] in ok_disks:
            disco['name']=dev["name"]
            disco['serial']=dev['serial']
            disco['type']=dev['type']
            disco['wwn']=dev['wwn']
            hard_drives.append(disco)
#print(hard_drives)
    return hard_drives


class Disk(object):
    """
    Hard Disk Drive
    """
    def __init__(self, dev):
        self.code = None
        self.serial = None
        self.dev = dev

    def retrieve_serial(self):
        self.serial = os.popen('sudo smartctl -x ' + path + ' | grep Serial') \
            .read().split(':')[1].replace(' ', '').replace('\n', '')

    def retrieve_code(self):
        """
        Retrieves the HDD code from T.A.R.A.L.L.O.
        :param path: The /dev/sdX path of the HDD
        :return: Either the HDD code or a 'sdX' string that will be used as filename
        """
        if tarallo_login():
            res = requests.get('tarallo_link' + '/v1/features/sn/' + self.serial, cookies=tarallo_cookie)
            if res.status_code == 200:
                self.code = res.json()['data'][0]
                if not simulate:
                    # Write stuff to the log file
                    pass
                else:
                    if not quiet:
                        print("Detected " + self.code + " on " + path)
            else:
                if not simulate:
                    # Write stuff to the log file
                    pass
                else:
                    if not quiet:
                        print("Code not found for " + path)
                self.code = path.split('/')[2]
        else:
            if not simulate:
                # Write stuff to the log file
                pass
            else:
                if not quiet:
                    print("Could not retrieve HDD code from T.A.R.A.L.L.O. for " + path)


class Task(Process):
    """
    Disk cleaning process
    """
    def __init__(self, disk):
        """
        :param disk: Disk object
        """
        super().__init__(self)
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
        sp.run(['sudo', 'badblocks', '-w', '-t', '0x00', '-o', self.disk.code, self.disk.dev])
        exit_code = sp.Popen('cat %s' % self.disk.code)
        if exit_code != 0:
            sp.run(['rm', '-f', self.disk.code])
        else:
            # TODO: Write on tarallo that the hard drive is broken
            # Write it in the turbofresa log file as well
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Automatically drill every single connected hard drive.')
    parser.add_argument('-s', '--shutdown', action='store_true', help='Shutdown the machine when everything is done.')
    parser.add_argument('-q', '--quiet', action='store_true', help='Run in background and suppress stdout.')
    parser.add_argument('-d', '--dry', action='store_true', help='Launch simulation.')
    parser.add_argument('--version', '-V', action='version', version='%(prog)s v.' + __version__)
    parser.set_defaults(shutdown=False)
    parser.set_defaults(quiet=False)
    parser.set_defaults(dry=False)
    args = parser.parse_args()
    quiet = args.quiet
    simulate = args.dry

    # ask_confirm()
    if not quiet:
        print("===> Detecting connected hard drives.")
    disks = detect_disks()
    tasks = []

    for d in disks:
        # TODO: add a method that adds disk to tarallo, create a Disk object (or a Tarallo.Item)
        # TODO: pass that to every other method from here onward
        tasks.append(Task(d))
        
    if not quiet:
        print("===> Cleaning disks")
    for t in tasks:
        if not simulate:
            t.start()
        else:
            if not quiet:
                print("Started cleaning")

    for t in tasks:
        if not simulate:
            t.join()
        else:
            if not quiet:
                print("Ended cleaning")

    if args.shutdown is True:
        if not simulate:
            sp.run(['sudo', 'shutdown'])
        else:
            if not quiet:
                print("System halted by the user.")
    if not quiet:
        print("Done.")
    exit(0)
