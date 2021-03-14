"""Unit tests for orbitpy.coveragecalculator module.
"""

import json
import os
import sys
import unittest
import numpy as np

import propcov
from orbitpy.coveragecalculator import CoverageCalculatorFactory, GridCoverage, PointingOptionsCoverage, PointingOptionsWithGridCoverage

class TestCoverageCalculatorFactory(unittest.TestCase):
  
    class DummyNewCoverageCalculator:
        def __init__(self, *args, **kwargs):
            pass
            
        def from_dict(self):
            return TestCoverageCalculatorFactory.DummyNewCoverageCalculator()

    def test___init__(self):
        factory = CoverageCalculatorFactory()

        # test the built-in coverage calculators are registered
        # Grid Coverage
        self.assertIn('Grid Coverage', factory._creators)
        self.assertEqual(factory._creators['Grid Coverage'], GridCoverage)
        # Pointing Options Coverage
        self.assertIn('Pointing Options Coverage', factory._creators)
        self.assertEqual(factory._creators['Pointing Options Coverage'], PointingOptionsCoverage)
        # Pointing Options With Grid Coverage
        self.assertIn('Pointing Options With Grid Coverage', factory._creators)
        self.assertEqual(factory._creators['Pointing Options With Grid Coverage'], PointingOptionsWithGridCoverage)

    def test_register_coverage_calculator(self):
        factory = CoverageCalculatorFactory()
        factory.register_coverage_calculator('New Cov Calc', TestCoverageCalculatorFactory.DummyNewCoverageCalculator)
        self.assertIn('New Cov Calc', factory._creators)
        self.assertEqual(factory._creators['New Cov Calc'], TestCoverageCalculatorFactory.DummyNewCoverageCalculator)
        # test the built-in coverage calculator remain registered after registration of new coverage calculator
        # Grid Coverage
        self.assertIn('Grid Coverage', factory._creators)
        self.assertEqual(factory._creators['Grid Coverage'], GridCoverage)
        # Pointing Options Coverage
        self.assertIn('Pointing Options Coverage', factory._creators)
        self.assertEqual(factory._creators['Pointing Options Coverage'], PointingOptionsCoverage)
        # Pointing Options With Grid Coverage
        self.assertIn('Pointing Options With Grid Coverage', factory._creators)
        self.assertEqual(factory._creators['Pointing Options With Grid Coverage'], PointingOptionsWithGridCoverage)

    def test_get_coverage_calculator(self):
        
        factory = CoverageCalculatorFactory()
        # register dummy coverage calculator
        factory.register_coverage_calculator('New Coverage Calc', TestCoverageCalculatorFactory.DummyNewCoverageCalculator)
        
        # test the coverage calculator model classes can be obtained depending on the input specifications
        # Grid Coverage
        specs = {"@type": 'Grid Coverage'} # in practice additional coverage calculator specs shall be present in the dictionary
        grid_cov = factory.get_coverage_calculator(specs)
        self.assertIsInstance(grid_cov, GridCoverage)
        # Pointing Options Coverage
        specs = {"@type": 'Pointing Options Coverage'} # in practice additional coverage calculator specs shall be present in the dictionary
        grid_cov = factory.get_coverage_calculator(specs)
        self.assertIsInstance(grid_cov, PointingOptionsCoverage)
        # Pointing Options With Grid Coverage
        specs = {"@type": 'Pointing Options With Grid Coverage'} # in practice additional coverage calculator specs shall be present in the dictionary
        grid_cov = factory.get_coverage_calculator(specs)
        self.assertIsInstance(grid_cov, PointingOptionsWithGridCoverage)

        # DummyNewCoverageCalculator
        specs = {"@type": 'New Coverage Calc'} # in practice additional coverage calculator specs shall be present in the dictionary
        new_prop = factory.get_coverage_calculator(specs)
        self.assertIsInstance(new_prop, TestCoverageCalculatorFactory.DummyNewCoverageCalculator)
    
