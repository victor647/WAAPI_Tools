# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'WorkUnitImporter.ui'
##
## Created by: Qt User Interface Compiler version 6.9.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
    QGroupBox, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_WorkUnitImporter(object):
    def setupUi(self, WorkUnitImporter):
        if not WorkUnitImporter.objectName():
            WorkUnitImporter.setObjectName(u"WorkUnitImporter")
        WorkUnitImporter.resize(356, 166)
        self.horizontalLayout_2 = QHBoxLayout(WorkUnitImporter)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.groupBox = QGroupBox(WorkUnitImporter)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setMaximumSize(QSize(120, 16777215))
        self.cbxImportEffects = QCheckBox(self.groupBox)
        self.cbxImportEffects.setObjectName(u"cbxImportEffects")
        self.cbxImportEffects.setGeometry(QRect(31, 120, 68, 20))
        self.cbxImportEffects.setChecked(True)
        self.cbxImportSourceFile = QCheckBox(self.groupBox)
        self.cbxImportSourceFile.setObjectName(u"cbxImportSourceFile")
        self.cbxImportSourceFile.setGeometry(QRect(31, 20, 71, 20))
        self.cbxImportSourceFile.setChecked(True)
        self.cbxImportConversion = QCheckBox(self.groupBox)
        self.cbxImportConversion.setObjectName(u"cbxImportConversion")
        self.cbxImportConversion.setGeometry(QRect(31, 80, 71, 20))
        self.cbxImportConversion.setChecked(True)
        self.cbxImportAttenuation = QCheckBox(self.groupBox)
        self.cbxImportAttenuation.setObjectName(u"cbxImportAttenuation")
        self.cbxImportAttenuation.setGeometry(QRect(31, 60, 71, 20))
        self.cbxImportAttenuation.setChecked(True)
        self.cbxImportBus = QCheckBox(self.groupBox)
        self.cbxImportBus.setObjectName(u"cbxImportBus")
        self.cbxImportBus.setGeometry(QRect(31, 100, 68, 20))
        self.cbxImportBus.setChecked(True)
        self.cbxImportRTPC = QCheckBox(self.groupBox)
        self.cbxImportRTPC.setObjectName(u"cbxImportRTPC")
        self.cbxImportRTPC.setGeometry(QRect(31, 40, 53, 20))
        self.cbxImportRTPC.setChecked(True)

        self.horizontalLayout_2.addWidget(self.groupBox)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.lblMissingAction = QLabel(WorkUnitImporter)
        self.lblMissingAction.setObjectName(u"lblMissingAction")

        self.horizontalLayout.addWidget(self.lblMissingAction)

        self.cbbMissingAction = QComboBox(WorkUnitImporter)
        self.cbbMissingAction.addItem("")
        self.cbbMissingAction.addItem("")
        self.cbbMissingAction.addItem("")
        self.cbbMissingAction.setObjectName(u"cbbMissingAction")

        self.horizontalLayout.addWidget(self.cbbMissingAction)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.btnStartImport = QPushButton(WorkUnitImporter)
        self.btnStartImport.setObjectName(u"btnStartImport")

        self.verticalLayout.addWidget(self.btnStartImport)

        self.lblCurrentObject = QLabel(WorkUnitImporter)
        self.lblCurrentObject.setObjectName(u"lblCurrentObject")

        self.verticalLayout.addWidget(self.lblCurrentObject)

        self.lblObjectCount = QLabel(WorkUnitImporter)
        self.lblObjectCount.setObjectName(u"lblObjectCount")

        self.verticalLayout.addWidget(self.lblObjectCount)


        self.horizontalLayout_2.addLayout(self.verticalLayout)


        self.retranslateUi(WorkUnitImporter)

        QMetaObject.connectSlotsByName(WorkUnitImporter)
    # setupUi

    def retranslateUi(self, WorkUnitImporter):
        WorkUnitImporter.setWindowTitle(QCoreApplication.translate("WorkUnitImporter", u"WorkUnit\u5bfc\u5165\u5de5\u5177", None))
        self.groupBox.setTitle(QCoreApplication.translate("WorkUnitImporter", u"\u5bfc\u5165\u5185\u5bb9", None))
        self.cbxImportEffects.setText(QCoreApplication.translate("WorkUnitImporter", u"\u6548\u679c\u5668", None))
        self.cbxImportSourceFile.setText(QCoreApplication.translate("WorkUnitImporter", u"\u97f3\u9891\u6837\u672c", None))
        self.cbxImportConversion.setText(QCoreApplication.translate("WorkUnitImporter", u"\u538b\u7f29\u8bbe\u7f6e", None))
        self.cbxImportAttenuation.setText(QCoreApplication.translate("WorkUnitImporter", u"\u8870\u51cf\u66f2\u7ebf", None))
        self.cbxImportBus.setText(QCoreApplication.translate("WorkUnitImporter", u"\u8f93\u51faBus", None))
        self.cbxImportRTPC.setText(QCoreApplication.translate("WorkUnitImporter", u"RTPC", None))
        self.lblMissingAction.setText(QCoreApplication.translate("WorkUnitImporter", u"\u627e\u4e0d\u5230\u540c\u540d\u5bf9\u8c61\u65f6", None))
        self.cbbMissingAction.setItemText(0, QCoreApplication.translate("WorkUnitImporter", u"\u521b\u5efa", None))
        self.cbbMissingAction.setItemText(1, QCoreApplication.translate("WorkUnitImporter", u"\u8b66\u544a", None))
        self.cbbMissingAction.setItemText(2, QCoreApplication.translate("WorkUnitImporter", u"\u5ffd\u7565", None))

        self.btnStartImport.setText(QCoreApplication.translate("WorkUnitImporter", u"\u9009\u62e9\u6587\u4ef6\u5e76\u5bfc\u5165", None))
        self.lblCurrentObject.setText("")
        self.lblObjectCount.setText("")
    # retranslateUi

