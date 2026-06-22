# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'UnityAssetManager.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QDialog, QHBoxLayout,
    QHeaderView, QPushButton, QSizePolicy, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_UnityAssetManager(object):
    def setupUi(self, UnityAssetManager):
        if not UnityAssetManager.objectName():
            UnityAssetManager.setObjectName(u"UnityAssetManager")
        UnityAssetManager.resize(548, 574)
        self.verticalLayout = QVBoxLayout(UnityAssetManager)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btnSelectAssetFolder = QPushButton(UnityAssetManager)
        self.btnSelectAssetFolder.setObjectName(u"btnSelectAssetFolder")

        self.horizontalLayout.addWidget(self.btnSelectAssetFolder)

        self.btnDeleteSelected = QPushButton(UnityAssetManager)
        self.btnDeleteSelected.setObjectName(u"btnDeleteSelected")

        self.horizontalLayout.addWidget(self.btnDeleteSelected)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.tblFileList = QTableWidget(UnityAssetManager)
        if (self.tblFileList.columnCount() < 4):
            self.tblFileList.setColumnCount(4)
        __qtablewidgetitem = QTableWidgetItem()
        self.tblFileList.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tblFileList.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tblFileList.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.tblFileList.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        self.tblFileList.setObjectName(u"tblFileList")
        self.tblFileList.setDragEnabled(True)
        self.tblFileList.setDragDropMode(QAbstractItemView.DragDrop)
        self.tblFileList.setSortingEnabled(True)

        self.verticalLayout.addWidget(self.tblFileList)


        self.retranslateUi(UnityAssetManager)

        QMetaObject.connectSlotsByName(UnityAssetManager)
    # setupUi

    def retranslateUi(self, UnityAssetManager):
        UnityAssetManager.setWindowTitle(QCoreApplication.translate("UnityAssetManager", u" Unity Wwise Asset\u7ba1\u7406", None))
        self.btnSelectAssetFolder.setText(QCoreApplication.translate("UnityAssetManager", u"\u9009\u62e9Wwise\u76ee\u5f55\u4e0bScriptableObject\u6587\u4ef6\u5939", None))
        self.btnDeleteSelected.setText(QCoreApplication.translate("UnityAssetManager", u"\u5220\u9664\u9009\u4e2d\u8d44\u6e90", None))
        ___qtablewidgetitem = self.tblFileList.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("UnityAssetManager", u"\u540d\u79f0", None));
        ___qtablewidgetitem1 = self.tblFileList.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("UnityAssetManager", u"\u7c7b\u578b", None));
        ___qtablewidgetitem2 = self.tblFileList.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("UnityAssetManager", u"\u72b6\u6001", None));
        ___qtablewidgetitem3 = self.tblFileList.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("UnityAssetManager", u"GUID", None));
    # retranslateUi

