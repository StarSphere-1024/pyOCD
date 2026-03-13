# Copyright (c) 2025 StarSphere. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test for nRF54LM20A target definition."""

import pytest
from unittest.mock import MagicMock

from pyocd.target.builtin.target_nRF54LM20A import NRF54LM20A
from pyocd.target.builtin import BUILTIN_TARGETS
from pyocd.core.memory_map import MemoryType


class TestNRF54LM20A:
    """Test cases for the nRF54LM20A target."""

    def test_import(self):
        """Verify the target class can be imported."""
        assert NRF54LM20A is not None
        assert NRF54LM20A.__name__ == "NRF54LM20A"

    def test_vendor(self):
        """Verify the vendor is set correctly."""
        assert NRF54LM20A.VENDOR == "Nordic Semiconductor"

    def test_builtin_target_registered(self):
        """Verify the target is registered in BUILTIN_TARGETS."""
        assert "nrf54lm20a" in BUILTIN_TARGETS
        assert BUILTIN_TARGETS["nrf54lm20a"] is NRF54LM20A

    def test_memory_map_regions(self):
        """Verify the memory map has the expected regions."""
        regions = list(NRF54LM20A.MEMORY_MAP)
        assert len(regions) == 3

        # Flash region
        flash = regions[0]
        assert flash.start == 0x0
        assert flash.length == 0x1FD000  # 2 MB
        assert flash.blocksize == 0x1000
        assert flash.type == MemoryType.FLASH
        assert flash.is_boot_memory is True

        # UICR region
        uicr = regions[1]
        assert uicr.start == 0x00FFD000
        assert uicr.length == 0x1000
        assert uicr.blocksize == 0x4
        assert uicr.type == MemoryType.FLASH
        assert uicr.is_testable is False
        assert uicr.is_erasable is False

        # RAM region
        ram = regions[2]
        assert ram.start == 0x20000000
        assert ram.length == 0x80000  # 512 KB
        assert ram.type == MemoryType.RAM

    def test_flash_algo(self):
        """Verify the flash algorithm is defined."""
        regions = list(NRF54LM20A.MEMORY_MAP)
        flash = regions[0]
        assert flash.algo is not None
        assert "instructions" in flash.algo
        assert "pc_init" in flash.algo
        assert "pc_unInit" in flash.algo
        assert "pc_program_page" in flash.algo
        assert "pc_erase_sector" in flash.algo
        assert "pc_eraseAll" in flash.algo
        assert flash.algo["flash_start"] == 0x0
        assert flash.algo["flash_size"] == 0x1FD000

    def test_flash_sector_sizes(self):
        """Verify flash sector sizes are correct."""
        regions = list(NRF54LM20A.MEMORY_MAP)
        flash = regions[0]
        sector_sizes = flash.algo["sector_sizes"]
        assert len(sector_sizes) == 2
        # Main flash area
        assert sector_sizes[0] == (0x0, 0x1FD000)
        # UICR area
        assert sector_sizes[1] == (0xFFD000, 0x1000)

    def test_check_flash_security_valid_device(self):
        """Verify check_flash_security handles valid device correctly."""
        # Create mock session
        mock_session = MagicMock()
        mock_session.options.get = MagicMock(return_value=False)

        # Create target instance
        target = NRF54LM20A(mock_session)

        # Mock the dp.read_dp to return a valid nRF54LM20A ID
        # Expected: target_id & 0xFFF == 0x289 and target_id & 0xF0000 == 0x90000
        target.dp = MagicMock()
        target.dp.read_dp = MagicMock(return_value=0x90289)
        target.ap_is_enabled = MagicMock(return_value=True)

        # Should not raise an exception
        target.check_flash_security()

        # Verify read_dp was called with correct register address
        target.dp.read_dp.assert_called_once_with(0x24)

    def test_check_flash_security_invalid_nordic_id(self):
        """Verify check_flash_security logs error for non-Nordic device."""
        mock_session = MagicMock()
        mock_session.options.get = MagicMock(return_value=False)

        target = NRF54LM20A(mock_session)
        target.dp = MagicMock()
        # Invalid Nordic ID (doesn't match 0x289)
        target.dp.read_dp = MagicMock(return_value=0x90000)
        target.ap_is_enabled = MagicMock(return_value=True)

        target.check_flash_security()

        target.dp.read_dp.assert_called_once_with(0x24)

    def test_check_flash_security_invalid_device_id(self):
        """Verify check_flash_security logs error for non-nRF54LM20A device."""
        mock_session = MagicMock()
        mock_session.options.get = MagicMock(return_value=False)

        target = NRF54LM20A(mock_session)
        target.dp = MagicMock()
        # Valid Nordic ID but invalid device ID (doesn't match 0x90000)
        target.dp.read_dp = MagicMock(return_value=0x80289)
        target.ap_is_enabled = MagicMock(return_value=True)

        target.check_flash_security()

        target.dp.read_dp.assert_called_once_with(0x24)

    def test_check_flash_security_ap_not_enabled_auto_unlock(self):
        """Verify check_flash_security performs mass erase when auto_unlock is enabled."""
        mock_session = MagicMock()
        mock_session.options.get = MagicMock(return_value=True)

        target = NRF54LM20A(mock_session)
        target.dp = MagicMock()
        target.dp.read_dp = MagicMock(return_value=0x90289)
        target.ap_is_enabled = MagicMock(return_value=False)
        target.mass_erase = MagicMock()

        target.check_flash_security()

        target.mass_erase.assert_called_once()

    def test_check_flash_security_ap_not_enabled_no_auto_unlock(self):
        """Verify check_flash_security does not mass erase when auto_unlock is disabled."""
        mock_session = MagicMock()
        mock_session.options.get = MagicMock(return_value=False)

        target = NRF54LM20A(mock_session)
        target.dp = MagicMock()
        target.dp.read_dp = MagicMock(return_value=0x90289)
        target.ap_is_enabled = MagicMock(return_value=False)
        target.mass_erase = MagicMock()

        target.check_flash_security()

        target.mass_erase.assert_not_called()
