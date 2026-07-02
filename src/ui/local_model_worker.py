from PyQt5.QtCore import QObject, pyqtSignal


class LocalModelWorker(QObject):
    finished = pyqtSignal(bool, str)

    def __init__(self, action, model_name):
        super().__init__()
        self.action = action
        self.model_name = model_name

    def run(self):
        from transcription import delete_model_cache, download_whisper_model

        try:
            if self.action == "download":
                success, message = download_whisper_model(self.model_name)
            elif self.action == "delete":
                if delete_model_cache(self.model_name):
                    success, message = True, f"Deleted cached files for {self.model_name}."
                else:
                    success, message = False, f"No cached files found for {self.model_name}."
            else:
                success, message = False, f"Unknown action: {self.action}"
        except Exception as exc:
            success, message = False, str(exc)

        self.finished.emit(success, message)
