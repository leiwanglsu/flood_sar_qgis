
from distutils.core import setup, Extension
from distutils import ccompiler
from setuptools import find_packages
import pybind11
cpp_args = ['/std:c++17']
print("Compiler is: ", ccompiler.get_default_compiler())
sfc_module = Extension(
    'rgrow_flood',
    sources=['region_grow.cpp'],
  
    include_dirs=[
      pybind11.get_include(False),
      pybind11.get_include(True ),
    ],
    language='c++',
    extra_compile_args=cpp_args)


setup(
    name="rgrow_flood",
    version='1.0.1',
    description='Python package for image object operations',
    ext_modules=[sfc_module],
    author='Lei Wang',
    author_email='leiwang@lsu.edu',
    packages=find_packages(),
    classifiers=[
    'Programming Language :: C++',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    ],
    python_requires='>=3.6'
)
