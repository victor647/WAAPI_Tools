# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'SyncTrim.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog,
    QHBoxLayout, QHeaderView, QLabel, QSizePolicy,
    QSpacerItem, QTableWidget, QVBoxLayout, QWidget)


class Ui_SyncTrim(object):
    def setupUi(self, SyncTrim):
        if not SyncTrim.objectName():
            SyncTrim.setObjectName(u"SyncTrim")
        SyncTrim.resize(960, 540)
        self.verticalLayout = QVBoxLayout(SyncTrim)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.lblHint = QLabel(SyncTrim)
        self.lblHint.setObjectName(u"lblHint")

        self.horizontalLayout.addWidget(self.lblHint)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.tblTrimInfo = QTableWidget(SyncTrim)
        self.tblTrimInfo.setObjectName(u"tblTrimInfo")
        self.tblTrimInfo.setAlternatingRowColors(True)
        self.tblTrimInfo.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tblTrimInfo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.verticalLayout.addWidget(self.tblTrimInfo)


        self.retranslateUi(SyncTrim)

        QMetaObject.connectSlotsByName(SyncTrim)
    # setupUi

    def retranslateUi(self, SyncTrim):
        SyncTrim.setWindowTitle(QCoreApplication.translate("SyncTrim", u"\u540c\u6b65\u88c1\u526a", None))
        self.lblHint.setText(QCoreApplication.translate("SyncTrim", u"AudioSource \u88c1\u526a\u4fe1\u606f", None))
    # retranslateUi
