# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'BankAssignmentMatrix.ui'
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
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QHeaderView,
    QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

class Ui_BankAssignmentMatrix(object):
    def setupUi(self, BankAssignmentMatrix):
        if not BankAssignmentMatrix.objectName():
            BankAssignmentMatrix.setObjectName(u"BankAssignmentMatrix")
        BankAssignmentMatrix.resize(476, 292)
        self.verticalLayout = QVBoxLayout(BankAssignmentMatrix)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btnAddRow = QPushButton(BankAssignmentMatrix)
        self.btnAddRow.setObjectName(u"btnAddRow")

        self.horizontalLayout.addWidget(self.btnAddRow)

        self.btnRemoveRow = QPushButton(BankAssignmentMatrix)
        self.btnRemoveRow.setObjectName(u"btnRemoveRow")

        self.horizontalLayout.addWidget(self.btnRemoveRow)

        self.btnAddColumn = QPushButton(BankAssignmentMatrix)
        self.btnAddColumn.setObjectName(u"btnAddColumn")

        self.horizontalLayout.addWidget(self.btnAddColumn)

        self.btnRemoveColumn = QPushButton(BankAssignmentMatrix)
        self.btnRemoveColumn.setObjectName(u"btnRemoveColumn")

        self.horizontalLayout.addWidget(self.btnRemoveColumn)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.tblMatrix = QTableWidget(BankAssignmentMatrix)
        if (self.tblMatrix.columnCount() < 3):
            self.tblMatrix.setColumnCount(3)
        __qtablewidgetitem = QTableWidgetItem()
        self.tblMatrix.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tblMatrix.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tblMatrix.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        if (self.tblMatrix.rowCount() < 5):
            self.tblMatrix.setRowCount(5)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tblMatrix.setVerticalHeaderItem(0, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.tblMatrix.setVerticalHeaderItem(1, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.tblMatrix.setVerticalHeaderItem(2, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.tblMatrix.setVerticalHeaderItem(3, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.tblMatrix.setVerticalHeaderItem(4, __qtablewidgetitem7)
        self.tblMatrix.setObjectName(u"tblMatrix")

        self.verticalLayout.addWidget(self.tblMatrix)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.btnFillWithChildren = QPushButton(BankAssignmentMatrix)
        self.btnFillWithChildren.setObjectName(u"btnFillWithChildren")

        self.horizontalLayout_2.addWidget(self.btnFillWithChildren)

        self.btnCreateBanks = QPushButton(BankAssignmentMatrix)
        self.btnCreateBanks.setObjectName(u"btnCreateBanks")

        self.horizontalLayout_2.addWidget(self.btnCreateBanks)

        self.btnAssignMedia = QPushButton(BankAssignmentMatrix)
        self.btnAssignMedia.setObjectName(u"btnAssignMedia")

        self.horizontalLayout_2.addWidget(self.btnAssignMedia)


        self.verticalLayout.addLayout(self.horizontalLayout_2)


        self.retranslateUi(BankAssignmentMatrix)

        QMetaObject.connectSlotsByName(BankAssignmentMatrix)
    # setupUi

    def retranslateUi(self, BankAssignmentMatrix):
        BankAssignmentMatrix.setWindowTitle(QCoreApplication.translate("BankAssignmentMatrix", u"SoundBank\u81ea\u52a8\u5206\u914d\u5de5\u5177", None))
        self.btnAddRow.setText(QCoreApplication.translate("BankAssignmentMatrix", u"\u6dfb\u52a0\u884c", None))
        self.btnRemoveRow.setText(QCoreApplication.translate("BankAssignmentMatrix", u"\u5220\u9664\u884c", None))
        self.btnAddColumn.setText(QCoreApplication.translate("BankAssignmentMatrix", u"\u6dfb\u52a0\u5217", None))
        self.btnRemoveColumn.setText(QCoreApplication.translate("BankAssignmentMatrix", u"\u5220\u9664\u5217", None))
        ___qtablewidgetitem = self.tblMatrix.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("BankAssignmentMatrix", u"1", None));
        ___qtablewidgetitem1 = self.tblMatrix.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("BankAssignmentMatrix", u"2", None));
        ___qtablewidgetitem2 = self.tblMatrix.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("BankAssignmentMatrix", u"3", None));
        ___qtablewidgetitem3 = self.tblMatrix.verticalHeaderItem(0)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("BankAssignmentMatrix", u"1", None));
        ___qtablewidgetitem4 = self.tblMatrix.verticalHeaderItem(1)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("BankAssignmentMatrix", u"2", None));
        ___qtablewidgetitem5 = self.tblMatrix.verticalHeaderItem(2)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("BankAssignmentMatrix", u"3", None));
        ___qtablewidgetitem6 = self.tblMatrix.verticalHeaderItem(3)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("BankAssignmentMatrix", u"4", None));
        ___qtablewidgetitem7 = self.tblMatrix.verticalHeaderItem(4)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("BankAssignmentMatrix", u"5", None));
        self.btnFillWithChildren.setText(QCoreApplication.translate("BankAssignmentMatrix", u"\u4f7f\u7528\u9009\u53d6\u5bf9\u8c61\u586b\u5145\u884c", None))
        self.btnCreateBanks.setText(QCoreApplication.translate("BankAssignmentMatrix", u"\u521b\u5efa\u65b0\u7684SoundBank", None))
        self.btnAssignMedia.setText(QCoreApplication.translate("BankAssignmentMatrix", u"\u5206\u914d\u5230\u5df2\u6709SoundBank", None))
    # retranslateUi

