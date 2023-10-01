import setuptools

setuptools.setup(
    name="telegram_task",
    version="0.0.2",
    author="Arka Equities & Securities",
    author_email="info@arkaequities.com",
    description="A telegram bot task manager wrapper.",
    # long_description="Utilities for data mining and auto-trading in Tehran Stock Exhchange. \
    #     Contains TSETMC API implementation and other useful interfaces for securities market \
    #     data catching and processing.",
    packages=setuptools.find_packages(),
    install_requires=["python-telegram-bot[socks]", "python-dotenv"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ]
)
