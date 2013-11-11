.. _available_actions:

List of available dispatcher actions
####################################

Dispatcher actions are of two main types:

* General purpose actions for systems based on OpenEmbedded, Debian or Ubuntu
* :ref:`android_specific_actions`

These actions are routinely tested as part of the LAVA functional tests
and results are available in this :term:`bundle stream` page:

https://staging.validation.linaro.org/dashboard/streams/anonymous/lava-functional-tests/bundles/

Individual tests are listed using the ``job_name`` in the linked JSON. To
see all results just for one job, enter the ``job_name`` in the Search
box of the bundle stream page.

General purpose actions
***********************

These actions are commonly used with test images based on OpenEmbedded,
Debian or Ubuntu.

.. _deploy_linaro_image:

Deploying a linaro image
========================

Use ``deploy_linaro_image`` to deploy a test image onto a target.
Typically this is the first command that runs in any LAVA test job::

 {
    "actions": [
        {
            "command": "deploy_linaro_image",
            "parameters": {
                "image": "http://images.validation.linaro.org/kvm-debian-wheezy.img.gz"
            }
        }
    ]
 }

Example functional test: **kvm-single-node**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/single-node-job/neil.williams/kvm-single-node.json

Available parameters
--------------------

* :term:`hwpack`: Linaro style hardware pack. Usually contains a boot
  loader(s), kernel, dtb, ramdisk. The parameter accepts http, local
  and scp urls::

   http://myserver.com/hw-pack.tar.gz
   file:///home/user/hw-pack.tar.gz
   scp://username@myserver.com:/home/user/hw-pack.tar.gz

* :term:`rootfs`: A tarball for the root file system.
  The parameter accepts http, local and scp urls::

   http://myserver.com/rootfs.tar.gz
   file:///home/user/rootfs.tar.gz
   scp://username@myserver.com:/home/user/rootfs.tar.gz

* image: A prebuilt image that includes both a hwpack and a rootfs or
  the equivalent binaries. The parameter accepts http, local and scp
  urls::

   http://myserver.com/prebuilt.img.gz
   file:///home/user/prebuilt.img.gz
   scp://username@myserver.com:/home/user/prebuilt.img.gz

* rootfstype: This is the filesystem type for the rootfs.
  (i.e. ext2, ext3, ext4...). The parameter accepts
  any string and is optional.

* bootloadertype: The type of bootloader a target is using.
  The parameter accepts any string and is optional.
  The default is ``u_boot``.

* :term:`role`: Determines which devices in a MultiNode group will
  use this action. The parameter accepts any string, the string must
  exactly match one of the roles specified in the :term:`device group`.

::

 {
    "actions": [
        {
            "command": "deploy_linaro_image",
            "parameters": {
                "rootfs": "http://<server>/<hw_pack>.tar.gz",
                "hwpack": "http://<server>/<rootfs>.tar.gz",
                "bootloadertype": "uefi"
            }
        }
    ]
 }
 
Example functional test: **model-express-group-multinode**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/multi-node-job/neil.williams/fastmodel-vexpress-group.json

.. _deploy_linaro_kernel:

Deploying a Linaro kernel with device tree blob
===============================================

Use ``deploy_linaro_kernel`` to deploy a kernel which uses on a
device tree blob::

   {
      "command": "deploy_linaro_kernel",
      "parameters": {
        "kernel": "http://community.validation.linaro.org/images/beagle/zImage",
        "ramdisk": "http://community.validation.linaro.org/images/beagle/uInitrd",
        "dtb": "http://community.validation.linaro.org/images/beagle/omap3-beagle-xm.dtb",
        "rootfs": "http://community.validation.linaro.org/images/qemu/beagle-nano.img.gz"
    }

Example functional test: **bootloader-lava-test-shell-multinode**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/multi-node-job/bootloader/bootloader-lava-test-shell-multinode.json

**qemu-kernel-boot**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/single-node-job/qemu/qemu-kernel-boot.json

Available parameters
--------------------

* ``kernel``:
* ``ramdisk``:
* ``dtb``:
* :term:`rootfs`:
* :term:`role`: Determines which devices in a MultiNode group will
  use this action. The parameter accepts any string, the string must
  exactly match one of the roles specified in the :term:`device group`.

.. _boot_linaro_image:

Booting a Linaro image
======================

Use ``boot_linaro_image`` to boot a test image that was deployed using
the ``deploy_linaro_image`` action::

 {
    "actions": [
        {
            "command": "deploy_linaro_image",
            "parameters": {
                "image": "http://images.validation.linaro.org/kvm-debian-wheezy.img.gz"
            }
        },
        {
            "command": "boot_linaro_image"
        }
    ]
 }


.. note:: It is not necessary to use ``boot_linaro_image`` if the next
   action in the test is ``lava_test_shell``.

Example functional test: **kvm-kernel-boot**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/single-node-job/qemu/kvm-kernel-boot.json

Interactive boot commands
-------------------------

::

 {
    "actions": [
        {
            "command": "boot_linaro_image",
            "parameters": {
                "interactive_boot_cmds": true,
                "options": [
                    "setenv autoload no",
                    "setenv pxefile_addr_r '0x50000000'",
                    "setenv kernel_addr_r '0x80200000'",
                    "setenv initrd_addr_r '0x81000000'",
                    "setenv fdt_addr_r '0x815f0000'",
                    "setenv initrd_high '0xffffffff'",
                    "setenv fdt_high '0xffffffff'",
                    "setenv loadkernel 'tftp ${kernel_addr_r} ${lava_kernel}'",
                    "setenv loadinitrd 'tftp ${initrd_addr_r} ${lava_ramdisk}; setenv initrd_size ${filesize}'",
                    "setenv loadfdt 'tftp ${fdt_addr_r} ${lava_dtb}'",
                    "setenv bootargs 'console=ttyO0,115200n8 root=/dev/ram0 ip=:::::eth0:dhcp'",
                    "setenv bootcmd 'dhcp; setenv serverip ${lava_server_ip}; run loadkernel; run loadinitrd; run loadfdt; bootz ${kernel_addr_r} ${initrd_addr_r} ${fdt_addr_r}'",
                    "boot"
                ]
            }
        }
    ]
 }

Example functional test: **bootloader-lava-test-shell-multinode**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/multi-node-job/bootloader/bootloader-lava-test-shell-multinode.json

Available parameters
--------------------

* ``interactive_boot_cmds``: boolean, defaults to false.
* ``options``: Optional array of strings which will be passed as boot commands.
* :term:`role`: Determines which devices in a MultiNode group will
  use this action. The parameter accepts any string, the string must
  exactly match one of the roles specified in the :term:`device group`.

.. _lava_test_shell:

Running tests in the test image
===============================

Use ``lava_test_shell`` to boot the deployed image and invoke a set of
tests defined in a YAML file::

 {
    "actions": [
        {
            "command": "deploy_linaro_image",
            "parameters": {
                "image": "http://images.validation.linaro.org/kvm-debian-wheezy.img.gz"
            }
        },
        {
            "command": "lava_test_shell",
            "parameters": {
                "testdef_repos": [
                    {
                        "git-repo": "http://staging.git.linaro.org/git-ro/people/neil.williams/temp-functional-tests.git",
                        "testdef": "multinode/multinode03.yaml"
                    }
                ]
            }
        }
    ]
 }

Example functional test: **kvm-group-multinode**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/multi-node-job/neil.williams/kvm-only-group.json

To run multiple tests without a reboot in between each test run, extra ``testdef_repos`` can be listed::

 {
    "actions": [
        {
            "command": "lava_test_shell",
            "parameters": {
                "testdef_repos": [
                    {
                        "git-repo": "git://git.linaro.org/qa/test-definitions.git",
                        "testdef": "ubuntu/smoke-tests-basic.yaml"
                    },
                    {
                        "git-repo": "http://staging.git.linaro.org/git-ro/lava-team/lava-functional-tests.git",
                        "testdef": "lava-test-shell/multi-node/multinode02.yaml"
                    }
                ],
                "timeout": 900
            }
        }
    ]
 }

Example functional test: **model-express-group-multinode**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/multi-node-job/neil.williams/fastmodel-vexpress-group.json

To run multiple tests with a reboot in between each test run, add extra ``lava_test_shell``
actions::

 {
    "actions": [
        {
            "command": "lava_test_shell",
            "parameters": {
                "testdef_repos": [
                    {
                        "git-repo": "git: //git.linaro.org/qa/test-definitions.git",
                        "testdef": "ubuntu/smoke-tests-basic.yaml"
                    }
                ],
                "timeout": 900
            }
        },
        {
            "command": "lava_test_shell",
            "parameters": {
                "testdef_repos": [
                    {
                        "git-repo": "http: //staging.git.linaro.org/git-ro/lava-team/lava-functional-tests.git",
                        "testdef": "lava-test-shell/multi-node/multinode02.yaml"
                    }
                ],
                "timeout": 900
            }
        }
    ]
 }

Example functional test: **bootloader-lava-test-shell-multinode**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/multi-node-job/bootloader/bootloader-lava-test-shell-multinode.json

Available parameters
--------------------

* ``testdef_repos``: See :ref:`test_repos`.
* ``testdef_urls``: URL of the test definition when not using a version
  control repository.
* ``timeout``: Allows you set a timeout for the action. Any integer
  value, optional.
* :term:`role`: Determines which devices in a MultiNode group will
  use this action. The parameter accepts any string, the string must
  exactly match one of the roles specified in the :term:`device group`.

Example functional test: **kvm-group-multinode**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/multi-node-job/neil.williams/kvm-only-group.json

To run multiple tests without a reboot in between each test run, extra ``testdef_repos`` can be listed::

    "actions": [
        {
            "command": "lava_test_shell",
            "parameters": {
                "testdef_repos": [
                    {
                        "git-repo": "git://git.linaro.org/qa/test-definitions.git",
                        "testdef": "ubuntu/smoke-tests-basic.yaml"
                    },
                    {
                        "git-repo": "http://staging.git.linaro.org/git-ro/lava-team/lava-functional-tests.git",
                        "testdef": "lava-test-shell/multi-node/multinode02.yaml"
                    }
                ],
                "timeout": 900
            }
        },

Example functional test: **model-express-group-multinode**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/multi-node-job/neil.williams/fastmodel-vexpress-group.json

To run multiple tests with a reboot in between each test run, add extra ``lava_test_shell``
actions::

* :term:`stream`: the bundle stream to which the results will be submitted.
  The user submitting the test must be able to upload to the specified
  stream.
* ``server``: The server to which the results will be submitted.

.. _android_specific_actions:

Android specific actions
************************

.. _deploy_linaro_android_image:

Deploying a Linaro Android image
================================

Use ``deploy_linaro_android_image`` to deploy an Android test image
onto a target. Typically this is the first command that runs in any
LAVA job to test Android::

 {
    "actions": [
        {
            "command": "deploy_linaro_android_image",
            "parameters": {
                "boot": "http://<server>/boot.bz2",
                "data": "http://http://<server>/userdata.bz2",
                "system": "http://http://<server>/system.bz2"
            }
        }
    ]
 }

Example functional test: **master-lava-android-test-multinode**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/multi-node-job/master/master-lava-android-test-multinode.json

Available parameters
--------------------

* ``boot``: Android ``boot.img`` or ``boot.bz2``. Typically this is
  a kernel image and ramdisk. The parameter accepts http, local and
  scp urls::

   http://myserver.com/boot.img
   file:///home/user/boot.img
   scp://username@myserver.com:/home/user/boot.img

* ``system``: Android ``system.img`` or ``system.bz2``. Typically 
  this is the system partition. The parameter accepts http, local and
  scp urls::

   http://myserver.com/system.img
   file:///home/user/system.img
   scp://username@myserver.com:/home/user/system.img

* ``data``: Android ``userdata.img`` or ``userdata.bz2``. Typically
  this is the data partition. The parameter accepts http, local and
  scp urls::

   http://myserver.com/userdata.img
   file:///home/user/userdata.img
   scp://username@myserver.com:/home/user/userdata.img

* :term:`rootfstype`: This is the filesystem type for the :term:`rootfs`.
  (i.e. ext2, ext3, ext4...). The parameter accepts any string and is
  optional. The default is ``ext4``.
* :term:`role`: Determines which devices in a MultiNode group will
  use this action. The parameter accepts any string, the string must
  exactly match one of the roles specified in the :term:`device group`.

Example functional test: **master-lava-android-test-multinode**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/multi-node-job/master/master-lava-android-test-multinode.json

Available parameters
--------------------

* ``boot``: Android ``boot.img`` or ``boot.bz2``. Typically this is
  a kernel image and ramdisk. The parameter accepts http, local and
  scp urls::

   http://myserver.com/boot.img
   file:///home/user/boot.img
   scp://username@myserver.com:/home/user/boot.img

* ``system``: Android ``system.img`` or ``system.bz2``. Typically 
  this is the system partition. The parameter accepts http, local and
  scp urls::

   http://myserver.com/system.img
   file:///home/user/system.img
   scp://username@myserver.com:/home/user/system.img

* ``data``: Android ``userdata.img`` or ``userdata.bz2``. Typically
  this is the data partition. The parameter accepts http, local and
  scp urls::

   http://myserver.com/userdata.img
   file:///home/user/userdata.img
   scp://username@myserver.com:/home/user/userdata.img

* :term:`rootfstype`: This is the filesystem type for the :term:`rootfs`.
  (i.e. ext2, ext3, ext4...). The parameter accepts any string and is
  optional. The default is ``ext4``.
* :term:`role`: Determines which devices in a MultiNode group will
  use this action. The parameter accepts any string, the string must
  exactly match one of the roles specified in the :term:`device group`.

.. _boot_linaro_android_image:

Booting a Linaro Android image
==============================

Use ``boot_linaro_android_image`` to boot an Android test image
that was deployed using the ``deploy_linaro_android_image`` action::

 {
    "actions": [
        {
            "command": "deploy_linaro_android_image",
            "parameters": {
                "boot": "http: //<server>/boot.bz2",
                "data": "http: //http: //<server>/userdata.bz2",
                "system": "http: //http: //<server>/system.bz2"
            }
        },
        {
            "command": "boot_linaro_android_image"
        }
    ]
 }

Example functional test: **master-job-defined-boot-cmds-android**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/single-node-job/master/master-job-defined-boot-cmds-android.json

Example functional test: **master-job-defined-boot-cmds-android**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/single-node-job/master/master-job-defined-boot-cmds-android.json

.. _lava_android_test_install:

Installing Android tests in a deployed Android image
====================================================

Use ``lava_android_test_install`` to invoke the installation of a
lava-android-test test::

 {
    "command": "lava_android_test_install",
    "parameters": {
        "tests": [
            "monkey"
        ]
    }
 }

Example functional test: **master-lava-android-test-multinode**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/multi-node-job/master/master-lava-android-test-multinode.json

Running Android tests in a deployed Android image
==================================================

.. _lava_android_test_run:

Use ``lava_android_test_run`` to invoke the execution of a
lava-android-test test::

 {
    "command": "lava_android_test_run",
    "parameters": {
        "test_name": "monkey"
    }
 }

Example functional test: **master-lava-android-test-multinode**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/multi-node-job/master/master-lava-android-test-multinode.json

Available parameters
--------------------

* ``test_name``: The name of the test you want to invoke from
  lava-android-test. Any string is accepted. If an unknown test is
  specified it will cause an error.
* ``option``: Allows you to add additional command line parameters to
  lava-android-test install. Any string is accepted. If an unknown
  option is specified it will cause an error.
* ``timeout``: Allows you set a timeout for the action. Any integer
  value, optional.
* :term:`role`: Determines which devices in a MultiNode group will
  use this action. The parameter accepts any string, the string must
  exactly match one of the roles specified in the :term:`device group`.

Example functional test: **master-lava-android-test-multinode**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/multi-node-job/master/master-lava-android-test-multinode.json

Available parameters
--------------------

* ``test_name``: The name of the test you want to invoke from
  lava-android-test. Any string is accepted. If an unknown test is
  specified it will cause an error.
* ``option``: Allows you to add additional command line parameters to
  lava-android-test install. Any string is accepted. If an unknown
  option is specified it will cause an error.
* ``timeout``: Allows you set a timeout for the action. Any integer
  value, optional.
* :term:`role`: Determines which devices in a MultiNode group will
  use this action. The parameter accepts any string, the string must
  exactly match one of the roles specified in the :term:`device group`.

.. _lava_android_test_shell:

Invoking a LAVA Android test shell
==================================

Use ``lava_android_test_shell`` to invoke the execution of a
lava-test-shell test(s)::

 {
    "command": "lava_test_shell",
    "parameters": {
        "testdef_urls": [
            "http://myserver.com/my_test.yaml"
        ],
        "timeout": 180
    }
 }

Example functional test: **master-boot-options-boot-cmds-lava-test-shell-android**::

http://staging.git.linaro.org/lava-team/lava-functional-tests.git/blob/HEAD:/single-node-job/master/master-boot-options-lava-test-shell-android.json:
