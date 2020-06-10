from apps.preprocessor import PreProcessor as _PreProcessor


class PreProcessor(_PreProcessor):
    def __init__(self, sid, myid, w3, *, contract=None, db, channel=None):
        super().__init__(sid, myid, w3, contract=contract, db=db, channel=channel)

    def start(self):
        super().start()
