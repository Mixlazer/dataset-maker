import Metashape
import os
from PySide2 import QtWidgets
from dataset_maker.finder_script_ver3 import core
from common.utils.ui import load_ui_widget, show_error

class MainDialog(core):
    NAME = "finder"

    def __init__(self, ui_file, parent=None):
        super().__init__()
        self.ui = load_ui_widget(os.path.join(os.path.dirname(__file__), "Interface2.ui"), parent=parent)
        self.chunk = Metashape.app.document.chunk
        for group in self.chunk.shapes.groups:
            self.ui.combobox_group.addItem(group.label)

        self.ui.Start_button.clicked.connect(self.start)

    def start(self):
        layer = self.ui.combobox_group.currentText()
        for group in self.chunk.shapes.groups:
            if group.label == layer:
                self.group = group
                break

        Images_size = self.ui.line_edit_image_size.text()
        if Images_size.isdigit():
            Images_size = int(Images_size)
            if 0 < Images_size < 4097:
                self.Images_size = Images_size
            else:
                show_error(_("Parameters error"), _("Images_size must be between 0 and 4097"))
                return
        else:
            show_error(_("Parameters error"), _("Images_size must be a positive integer"))
            return

        Test = self.ui.Test_percentages.text()
        if Test.isdigit():
            Test = int(Test)
            if 0 < Test < 101:
                self.Test = Test
            else:
                show_error(_("Parameters error"), _("Test must be between 0 and 100"))
                return
        else:
            show_error(_("Parameters error"), _("Test must be a positive integer"))
            return

        Train = self.ui.Train_percentages.text()
        if Train.isdigit():
            Train = int(Train)
            if 0 < Train < 101:
                self.Train = Train
            else:
                show_error(_("Parameters error"), _("Train must be between 0 and 100"))
                return
        else:
            show_error(_("Parameters error"), _("Train must be a positive integer"))
            return

        Val = self.ui.Val_percentages.text()
        if Val.isdigit():
            Val = int(Val)
            if 0 < Val < 101:
                self.Val = Val
            else:
                show_error(_("Parameters error"), _("Val must be between 0 and 100"))
                return
        else:
            show_error(_("Parameters error"), _("Val must be a positive integer"))
            return

        total_percentage = int(Test) + int(Train) + int(Val)

        if total_percentage > 100:
            show_error(_("Parameters error"), _("Sum of percentages cannot be greater than 100"))
            return

        elif total_percentage < 100:
            show_error(_("Parameters error"), _("Sum of percentages cannot be less than 100"))
            return

        percentages = [Test, Train, Val]

        Result_Path= self.ui.Path.text()
        if isinstance(Result_Path, str):
            Result_Path = Result_Path.replace('\\', '/')
        else:
            show_error(_("Parameters error"), _("Result_Path is not a string"))
            return


        self.ui.Start_button.setEnabled(False)

        self.process_metashape_data(layer, Result_Path, percentages, Images_size)

        self.ui.Start_button.setEnabled(True)

def main(trans=None):
    if trans is not None:
        trans.install()
        _ = trans.gettext

    app = QtWidgets.QApplication.instance()
    parent = app.activeWindow()

    dialog = MainDialog(parent)
    dialog.ui.show()
    result = dialog.ui.exec_()
    if result:
        pass


if __name__ == "__main__":
    main()