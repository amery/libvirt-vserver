/*
 * node_device.h: node device enumeration
 *
 * Copyright (C) 2008 Virtual Iron Software, Inc.
 * Copyright (C) 2008 David F. Lively
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307  USA
 *
 * Author: David F. Lively <dlively@virtualiron.com>
 */

#ifndef __VIR_NODE_DEVICE_H__
#define __VIR_NODE_DEVICE_H__

#include "internal.h"
#include "driver.h"
#include "node_device_conf.h"

#define LINUX_SYSFS_SCSI_HOST_PREFIX "/sys/class/scsi_host"
#define LINUX_SYSFS_SCSI_HOST_POSTFIX "device"
#define LINUX_SYSFS_FC_HOST_PREFIX "/sys/class/fc_host/"

#define VPORT_CREATE 0
#define VPORT_DELETE 1
#define LINUX_SYSFS_VPORT_CREATE_POSTFIX "/vport_create"
#define LINUX_SYSFS_VPORT_DELETE_POSTFIX "/vport_delete"

#define LINUX_NEW_DEVICE_WAIT_TIME 60

#ifdef HAVE_HAL
int halNodeRegister(void);
#endif
#ifdef HAVE_DEVKIT
int devkitNodeRegister(void);
#endif

void nodeDeviceLock(virDeviceMonitorStatePtr driver);
void nodeDeviceUnlock(virDeviceMonitorStatePtr driver);

void registerCommonNodeFuncs(virDeviceMonitorPtr mon);

int nodedevRegister(void);

#endif /* __VIR_NODE_DEVICE_H__ */