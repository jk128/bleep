# bleep: BLE Abstraction Library for Python
#
# Copyright (c) 2015 Matthew Else
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# 2/3 compatibility
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from future.utils import bytes_to_native_str, native_str_to_bytes
from future.builtins import int, bytes

from uuid import UUID

from .util import is_short_uuid, DESC_UUIDS, CHAR_UUIDS, UUIDAccessor

class BLEAttribute:
    """Represents a single GATT Attribute (either a Descriptor or a Characteristic)

    Attributes:
        device (BLEDevice): The root BLEDevice object
        value_handle (int): This attribute's value handle
        uuid (UUID):        This attribute's UUID
    """

    def __init__(self, device, handle, uuid):
        """Creates an instance of BLEAttribute.

        Note:
            This should not be used directly, unless being subclassed.

        Args:
            device (BLEDevice): BLEDevice object of which this is an attribute
            handle (int): The numeric handle represented by this object
            uuid (UUID): The uuid representing this particular attribute
        """
        self.device = device
        self.value_handle = handle
        self.uuid = uuid

        # Register us for updates :)
        self.device.register_handle(self.value_handle, self)

        # Allow us to propagate callbacks
        self._notification_callbacks = []
        self._indication_callbacks = []

    def shortest_uuid(self):
        """Returns a string containing the shortest unique representation of the UUID.

        Returns:
            str: A textual representation of the UUID either in 16-bit form or 128-bit form
        """
        if is_short_uuid(self.uuid):
            return str(self.uuid)[4:8]
        else:
            return str(self.uuid)

    def read(self):
        """Reads the value of this attribute from the device. (Blocking)

        Returns:
            bytes: Data read from the device
        """
        return self.device.read_handle(self.value_handle)

    def write(self, data, response=True):
        """Writes data to the device. (Blocking)

        Args:
            data (bytes): Data to be written to this handle
            response (Optional[bool]): Whether the data should be written with, or
                without response.
        """
        return self.device.write_handle(self.value_handle, data, response)

    def notify(self, function):
        """Register a function to be called when a notification is received.

        Args:
            function (Callable[[bytes], None]): The function to be called:
                It must take data as its only parameter.
        """
        self._notification_callbacks.append(function)

    def indicate(self, function):
        """Register a function to be called when a indication is received.

        Args:
            function (Callable[[bytes], None]): The function to be called:
                It must take data as its only parameter.
        """
        self._indication_callbacks.append(function)

    def _on_notification(self, data):
        for callback in self._notification_callbacks:
            callback(data)

    def _on_indication(self, data):
        for callback in self._indication_callbacks:
            callback(data)

    def __repr__(self):
        raise NotImplementedError()

class BLEDescriptor(BLEAttribute):
    """Represents a single BLE Descriptor"""

    def __init__(self, device, handle, uuid):
        """Creates an instance of BLEAttribute.

        Args:
            device (BLEDevice): BLEDevice object of which this is an descriptor
            handle (int): The numeric handle represented by this object
            uuid (UUID): The uuid representing this particular descriptor
        """
        super(BLEDescriptor, self).__init__(device, handle, uuid)

    def __repr__(self):
        return '%s' % self.shortest_uuid() if self.shortest_uuid() not in DESC_UUIDS else DESC_UUIDS[self.shortest_uuid()]['name']

class BLECharacteristic:
    """Represents a single BLE Characteristic

    Attributes:
        handle (int): The BLE Characteristic Handle
        properties (int): Specifies whether certain operations are valid for
            this characteristic.
        descriptor (UUIDAccessor): Allows dictionary-like access to _unique_
            descriptors.
        descriptors (UUIDAccessor): Allows dictionary-like access to all descriptors.
            BLECharacteristic.descriptors[UUID] always returns a list of BLEDescriptors
    """

    def __init__(self, device, handle, value_handle, end_handle, uuid, properties):
        """Creates an instance of BLEAttribute.

        Args:
            device (BLEDevice): BLEDevice object of which this is an descriptor
            handle (int): The numeric handle represented by this object
            uuid (UUID): The uuid representing this particular descriptor
        """
        super(BLECharacteristic, self).__init__(self, device, value_handle, uuid)

        self.handle = handle
        self.end_handle = end_handle
        self.properties = properties

        self._descriptors = self._discover_descriptors()

        self.descriptor = UUIDAccessor(self._descriptors)
        self.descriptors = UUIDAccessor(self._descriptors, True)

    def _discover_descriptors(self):
        descriptors = {}

        if self.value_handle + 1 > self.end_handle:
            return descriptors

        for descriptor in self.device.requester.discover_descriptors(self.value_handle + 1, self.end_handle):
            try:
                desc = BLEDescriptor(self.device, descriptor['handle'], UUID(descriptor['uuid']))

                if desc.uuid in descriptors:
                    descriptors[desc.uuid].append(desc)
                else:
                    descriptors[desc.uuid] = [desc]
            except RuntimeError:
                # pygattlib returns a RuntimeError if the device responds with an error
                # which also happens when a descriptor cannot be found.
                pass

        return desc

    def __repr__(self):
        return self.shortest_uuid() if self.shortest_uuid() not in CHAR_UUIDS else CHAR_UUIDS[self.shortest_uuid()]['name']
