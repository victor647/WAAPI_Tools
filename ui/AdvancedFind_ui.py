# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'AdvancedFind.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
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
    QHBoxLayout, QPushButton, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_AdvancedFind(object):
    def setupUi(self, AdvancedFindWindow):
        if not AdvancedFindWindow.objectName():
            AdvancedFindWindow.setObjectName(u"AdvancedFindWindow")
        AdvancedFindWindow.resize(340, 180)
        AdvancedFindWindow.setMinimumSize(QSize(340, 0))
        self.verticalLayout = QVBoxLayout(AdvancedFindWindow)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.cbxRecursiveFind = QCheckBox(AdvancedFindWindow)
        self.cbxRecursiveFind.setObjectName(u"cbxRecursiveFind")
        self.cbxRecursiveFind.setChecked(True)

        self.verticalLayout.addWidget(self.cbxRecursiveFind)

        self.cbxKeepSelf = QCheckBox(AdvancedFindWindow)
        self.cbxKeepSelf.setObjectName(u"cbxKeepSelf")

        self.verticalLayout.addWidget(self.cbxKeepSelf)

        self.layoutFindChildType = QHBoxLayout()
        self.layoutFindChildType.setObjectName(u"layoutFindChildType")
        self.cbbFindChildType = QComboBox(AdvancedFindWindow)
        self.cbbFindChildType.setObjectName(u"cbbFindChildType")

        self.layoutFindChildType.addWidget(self.cbbFindChildType)

        self.btnFindChildType = QPushButton(AdvancedFindWindow)
        self.btnFindChildType.setObjectName(u"btnFindChildType")

        self.layoutFindChildType.addWidget(self.btnFindChildType)


        self.verticalLayout.addLayout(self.layoutFindChildType)

        self.buttonRow = QHBoxLayout()
        self.buttonRow.setObjectName(u"buttonRow")
        self.buttonSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonRow.addItem(self.buttonSpacer)

        self.btnClose = QPushButton(AdvancedFindWindow)
        self.btnClose.setObjectName(u"btnClose")

        self.buttonRow.addWidget(self.btnClose)


        self.verticalLayout.addLayout(self.buttonRow)


        self.retranslateUi(AdvancedFindWindow)

        QMetaObject.connectSlotsByName(AdvancedFindWindow)
    # setupUi

    def retranslateUi(self, AdvancedFindWindow):
        AdvancedFindWindow.setWindowTitle(QCoreApplication.translate("AdvancedFind", u"\u9ad8\u7ea7\u67e5\u627e", None))
        self.cbxRecursiveFind.setText(QCoreApplication.translate("AdvancedFind", u"\u9012\u5f52\u67e5\u627e", None))
        self.cbxKeepSelf.setText(QCoreApplication.translate("AdvancedFind", u"\u4fdd\u7559\u539f\u59cb\u5c42\u7ea7", None))
        self.btnFindChildType.setText(QCoreApplication.translate("AdvancedFind", u"\u67e5\u627e\u7279\u5b9a\u7c7b\u578b\u7684\u5b50\u5bf9\u8c61", None))
        self.btnClose.setText(QCoreApplication.translate("AdvancedFind", u"\u5173\u95ed", None))
    # retranslateUi

