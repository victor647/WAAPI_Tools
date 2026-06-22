# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ProgressBar.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QLabel, QProgressBar,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_ProgressBar(object):
    def setupUi(self, ProgressBar):
        if not ProgressBar.objectName():
            ProgressBar.setObjectName(u"ProgressBar")
        ProgressBar.resize(342, 62)
        self.verticalLayout = QVBoxLayout(ProgressBar)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.pgbSearching = QProgressBar(ProgressBar)
        self.pgbSearching.setObjectName(u"pgbSearching")
        font = QFont()
        font.setPointSize(9)
        self.pgbSearching.setFont(font)
        self.pgbSearching.setValue(0)

        self.verticalLayout.addWidget(self.pgbSearching)

        self.lblCurrentWorking = QLabel(ProgressBar)
        self.lblCurrentWorking.setObjectName(u"lblCurrentWorking")
        font1 = QFont()
        font1.setFamilies([u"Helvetica"])
        font1.setPointSize(9)
        self.lblCurrentWorking.setFont(font1)

        self.verticalLayout.addWidget(self.lblCurrentWorking)


        self.retranslateUi(ProgressBar)

        QMetaObject.connectSlotsByName(ProgressBar)
    # setupUi

    def retranslateUi(self, ProgressBar):
        ProgressBar.setWindowTitle(QCoreApplication.translate("ProgressBar", u"\u6b63\u5728\u8fdb\u884c\u5904\u7406\u2026\u2026", None))
        self.lblCurrentWorking.setText(QCoreApplication.translate("ProgressBar", u"\u5f53\u524d\u6b63\u5728\u5904\u7406", None))
    # retranslateUi

