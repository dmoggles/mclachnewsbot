from setuptools import find_packages, setup

setup(
    name="mclachnewsbot",
    packages=find_packages(exclude=["mclachnewsbot_tests"]),
    install_requires=[
        "dagster",
        "dagster-cloud"
    ],
    extras_require={"dev": ["dagster-webserver", "pytest"]},
)
