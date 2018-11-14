from pstats import Stats, SortKey

stats = Stats('prof/combined.prof')

stats.sort_stats(SortKey.CUMULATIVE).print_stats()
