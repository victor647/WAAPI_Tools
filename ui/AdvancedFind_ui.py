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

from libraries.widgets.multi_select_combo import MultiSelectCombo

class Ui_AdvancedFind(object):
    def setupUi(self, AdvancedFindWindow):
        if not AdvancedFindWindow.objectName():
            AdvancedFindWindow.setObjectName(u"AdvancedFindWindow")
        AdvancedFindWindow.resize(340, 96)
        AdvancedFindWindow.setMinimumSize(QSize(340, 0))
        self.verticalLayout = QVBoxLayout(AdvancedFindWindow)
        self.verticalLayout.setSpacing(4)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(6, 6, 6, 6)
        self.cbxKeepSelf = QCheckBox(AdvancedFindWindow)
        self.cbxKeepSelf.setObjectName(u"cbxKeepSelf")

        self.verticalLayout.addWidget(self.cbxKeepSelf)

        self.layoutFindProperty = QHBoxLayout()
        self.layoutFindProperty.setSpacing(4)
        self.layoutFindProperty.setObjectName(u"layoutFindProperty")
        self.layoutFindProperty.setContentsMargins(0, 0, 0, 0)
        self.cbbFindProperty = QComboBox(AdvancedFindWindow)
        self.cbbFindProperty.addItem("")
        self.cbbFindProperty.addItem("")
        self.cbbFindProperty.addItem("")
        self.cbbFindProperty.addItem("")
        self.cbbFindProperty.addItem("")
        self.cbbFindProperty.addItem("")
        self.cbbFindProperty.addItem("")
        self.cbbFindProperty.setObjectName(u"cbbFindProperty")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.cbbFindProperty.sizePolicy().hasHeightForWidth())
        self.cbbFindProperty.setSizePolicy(sizePolicy)
        self.cbbFindProperty.setMinimumSize(QSize(120, 0))

        self.layoutFindProperty.addWidget(self.cbbFindProperty)

        self.btnFindProperty = QPushButton(AdvancedFindWindow)
        self.btnFindProperty.setObjectName(u"btnFindProperty")

        self.layoutFindProperty.addWidget(self.btnFindProperty)


        self.verticalLayout.addLayout(self.layoutFindProperty)

        self.layoutFindChildType = QHBoxLayout()
        self.layoutFindChildType.setSpacing(4)
        self.layoutFindChildType.setObjectName(u"layoutFindChildType")
        self.layoutFindChildType.setContentsMargins(0, 0, 0, 0)
        self.cbbFindChildType = MultiSelectCombo(AdvancedFindWindow)
        self.cbbFindChildType.setObjectName(u"cbbFindChildType")

        self.layoutFindChildType.addWidget(self.cbbFindChildType)

        self.btnFindChildType = QPushButton(AdvancedFindWindow)
        self.btnFindChildType.setObjectName(u"btnFindChildType")

        self.layoutFindChildType.addWidget(self.btnFindChildType)


        self.verticalLayout.addLayout(self.layoutFindChildType)

        self.verticalSpacer = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(AdvancedFindWindow)

        QMetaObject.connectSlotsByName(AdvancedFindWindow)
    # setupUi

    def retranslateUi(self, AdvancedFindWindow):
        AdvancedFindWindow.setWindowTitle(QCoreApplication.translate("AdvancedFind", u"\u9ad8\u7ea7\u67e5\u627e", None))
        self.cbxKeepSelf.setText(QCoreApplication.translate("AdvancedFind", u"\u4fdd\u7559\u539f\u59cb\u5c42\u7ea7", None))
        self.cbbFindProperty.setItemText(0, QCoreApplication.translate("AdvancedFind", u"Attenuation", None))
        self.cbbFindProperty.setItemText(1, QCoreApplication.translate("AdvancedFind", u"Conversion", None))
        self.cbbFindProperty.setItemText(2, QCoreApplication.translate("AdvancedFind", u"OutputBus", None))
        self.cbbFindProperty.setItemText(3, QCoreApplication.translate("AdvancedFind", u"SwitchGroupOrStateGroup", None))
        self.cbbFindProperty.setItemText(4, QCoreApplication.translate("AdvancedFind", u"DefaultSwitchOrState", None))
        self.cbbFindProperty.setItemText(5, QCoreApplication.translate("AdvancedFind", u"UserAuxSend0", None))
        self.cbbFindProperty.setItemText(6, QCoreApplication.translate("AdvancedFind", u"ReflectionsAuxSend", None))

        self.btnFindProperty.setText(QCoreApplication.translate("AdvancedFind", u"\u67e5\u627e\u5bf9\u5e94\u5c5e\u6027\u5f15\u7528\u7684\u5bf9\u8c61", None))
        self.btnFindChildType.setText(QCoreApplication.translate("AdvancedFind", u"\u67e5\u627e\u7279\u5b9a\u7c7b\u578b\u7684\u5b50\u5bf9\u8c61", None))
    # retranslateUi

