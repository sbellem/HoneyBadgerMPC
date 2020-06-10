from apps.mpcserver import runner


if __name__ == "__main__":
    import asyncio

    import toml

    from apps.httpserver import HTTPServer
    from apps.parsers import ServerArgumentParser
    from apps.masks.mpcprogrunner import MPCProgRunner

    from apps.asynchromix2.preprocessor import PreProcessor

    # arg parsing
    parser = ServerArgumentParser()
    args = parser.parse_args()

    # read config and merge with cmdline args -- cmdline args have priority
    config = toml.load(args.config_path)
    _args = parser.post_process_args(args, config)

    asyncio.run(
        runner(
            "sid",
            _args["myid"],
            host=_args["host"],
            mpc_port=_args["mpc_port"],
            peers=_args["peers"],
            w3=_args["w3"],
            contract_context=_args["contract_context"],
            db=_args["db"],
            http_context={"host": _args["host"], "port": _args["http_port"]},
            preprocessor_class=PreProcessor,
            httpserver_class=HTTPServer,
            mpcprogrunner_class=MPCProgRunner,
        )
    )
