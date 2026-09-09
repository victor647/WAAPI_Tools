# Form implementation generated from reading UI file 'ExportObjectList.ui'
#
# Created by: Qt User Interface Compiler (PySide6)
#
# WARNING! All changes made in this file will be lost when recompiling UI file!


from PySide6 import QtCore, QtGui, QtWidgets


class Ui_ExportObjectList(object):
    def setupUi(self, ExportObjectList):
        ExportObjectList.setObjectName("ExportObjectList")
        ExportObjectList.resize(360, 520)
        self.verticalLayout = QtWidgets.QVBoxLayout(ExportObjectList)
        self.verticalLayout.setObjectName("verticalLayout")
        self.lblHint = QtWidgets.QLabel(parent=ExportObjectList)
        self.lblHint.setObjectName("lblHint")
        self.verticalLayout.addWidget(self.lblHint)
        self.scrollArea = QtWidgets.QScrollArea(parent=ExportObjectList)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.wgtCheckboxes = QtWidgets.QWidget()
        self.wgtCheckboxes.setGeometry(QtCore.QRect(0, 0, 338, 420))
        self.wgtCheckboxes.setObjectName("wgtCheckboxes")
        self.layCheckboxes = QtWidgets.QVBoxLayout(self.wgtCheckboxes)
        self.layCheckboxes.setSpacing(6)
        self.layCheckboxes.setObjectName("layCheckboxes")
        self.scrollArea.setWidget(self.wgtCheckboxes)
        self.verticalLayout.addWidget(self.scrollArea)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.btnSelectAll = QtWidgets.QPushButton(parent=ExportObjectList)
        self.btnSelectAll.setObjectName("btnSelectAll")
        self.horizontalLayout.addWidget(self.btnSelectAll)
        self.btnSelectNone = QtWidgets.QPushButton(parent=ExportObjectList)
        self.btnSelectNone.setObjectName("btnSelectNone")
        self.horizontalLayout.addWidget(self.btnSelectNone)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.btnCancel = QtWidgets.QPushButton(parent=ExportObjectList)
        self.btnCancel.setObjectName("btnCancel")
        self.horizontalLayout.addWidget(self.btnCancel)
        self.btnExport = QtWidgets.QPushButton(parent=ExportObjectList)
        self.btnExport.setObjectName("btnExport")
        self.horizontalLayout.addWidget(self.btnExport)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(ExportObjectList)
        QtCore.QMetaObject.connectSlotsByName(ExportObjectList)

    def retranslateUi(self, ExportObjectList):
        _translate = QtCore.QCoreApplication.translate
        ExportObjectList.setWindowTitle(_translate("ExportObjectList", "导出对象列表"))
        self.lblHint.setText(_translate("ExportObjectList", "请勾选需要导出的属性："))
        self.btnSelectAll.setText(_translate("ExportObjectList", "全选"))
        self.btnSelectNone.setText(_translate("ExportObjectList", "全不选"))
        self.btnCancel.setText(_translate("ExportObjectList", "取消"))
        self.btnExport.setText(_translate("ExportObjectList", "导出"))

