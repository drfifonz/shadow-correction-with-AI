import torch
import torch.nn as nn
import torch.nn.functional as F

from typing import Any


class ResidualBlock(nn.Module):
    def __init__(self, in_features):
        super(ResidualBlock, self).__init__()

        conv_block = [
            nn.ReflectionPad2d(1),
            nn.Conv2d(in_features, in_features, 3),
            nn.InstanceNorm2d(in_features),
            nn.ReLU(inplace=True),
            nn.ReflectionPad2d(1),
            nn.Conv2d(in_features, in_features, 3),
            nn.InstanceNorm2d(in_features),
        ]

        self.conv_block = nn.Sequential(*conv_block)

    def forward(self, x):
        return x + self.conv_block(x)


class Deshadower(nn.Module):
    def __init__(
        self,
        out_channels: int = 3,
        in_channels: int = 3,
        res_blocks: int = 9,
        downsampling_iterations: int = 2,
        upsampling_iterations: int = 2,
    ):
        super(Deshadower, self).__init__()

        # Initial conv layer
        self.model = nn.Sequential(
            nn.ReflectionPad2d(3),
            nn.Conv2d(
                in_channels=in_channels,
                out_channels=(out_features := 64),
                kernel_size=7,
            ),
            nn.InstanceNorm2d(64),
            nn.ReLU(inplace=True),
        )

        in_features = out_features
        out_features = in_features * 2

        downsampling_block = (
            nn.Conv2d(
                in_channels=in_features,
                out_channels=out_features,
                kernel_size=3,
                stride=2,
                padding=1,
            ),
            nn.InstanceNorm2d(out_features),
            nn.ReLU(inplace=True),
        )

        for num in range(downsampling_iterations):
            # in_channels = out_channels
            # out_channels = in_channels * 2
            self.model, *_ = map(
                self.model.append, self.__downsampling_block(in_features, out_features)
            )
            in_features = out_features
            out_features = in_features * 2

        # residual blocks
        residual_block = (
            nn.ReflectionPad2d(1),
            nn.Conv2d(in_channels=in_features, out_channels=in_features, kernel_size=3),
            nn.InstanceNorm2d(in_features),
            nn.ReLU(inplace=True),
            nn.ReflectionPad2d(1),
            nn.Conv2d(in_channels=in_features, out_channels=in_features, kernel_size=3),
            nn.InstanceNorm2d(in_features),
        )

        if res_blocks <= 0:
            raise Exception(
                f"res_blocks number should be positive number (it's: {res_blocks})"
            )
        model_temp = []
        # in_features = out_features
        for num in range(res_blocks):
            # self.model, *_ = map(
            #     self.model.append, self.__residual_block(in_features, out_features)
            # )
            self.model.append(ResidualBlock(in_features))
            # print(
            #     # f"in_features: {in_features}, out_features: {out_features}\tafter residual num: {num+1}\n "
            # )
        # self.model.append(*model_temp)
        out_features = in_features // 2

        print(
            # f"in_features: {in_features}, out_features: {out_features}\tb4 upsampling\n "
        )
        # print("upsampling block")
        upsampling_block = (
            nn.ConvTranspose2d(
                in_channels=in_features,
                out_channels=out_features,
                kernel_size=3,
                stride=2,
                padding=1,
                output_padding=1,
            ),
            nn.InstanceNorm2d(out_features),
            nn.ReLU(inplace=True),
        )

        for num in range(upsampling_iterations):
            self.model, *_ = map(
                self.model.append, self.__upsampling_block(in_features, out_features)
            )
            in_features = out_features
            out_features = in_features // 2
            # in_channels = out_channels
            # out_channels = in_channels // 2
            print(
                # f"in_features: {in_features}, out_features: {out_features}\tafter upsampling num: {num+1}\n "
            )
        # print("------------------------------------")
        # print(self.model)
        # print("------------------------------------")
        # raise
        # output layer
        self.model.append(nn.ReflectionPad2d(3))
        self.model.append(nn.Conv2d(64, out_channels, 7))

        # print("------------------------------------")
        # print(self.model)
        # print("DESHADOWER")
        # print("------------------------------------")
        # raise

    def forward(self, x: torch.Tensor):
        # print(x.shape)

        # could be something wrong with forward function

        return (self.model(x) + x).tanh

    def __downsampling_block(self, in_features: int, out_features: int) -> tuple:
        ds_block = (
            nn.Conv2d(
                in_channels=in_features,
                out_channels=out_features,
                kernel_size=3,
                stride=2,
                padding=1,
            ),
            nn.InstanceNorm2d(out_features),
            nn.ReLU(inplace=True),
        )
        return ds_block

    def __residual_block(self, in_features: int, out_features: int) -> tuple:
        residual_block = (
            nn.ReflectionPad2d(1),
            nn.Conv2d(in_channels=in_features, out_channels=in_features, kernel_size=3),
            nn.InstanceNorm2d(in_features),
            nn.ReLU(inplace=True),
            nn.ReflectionPad2d(1),
            nn.Conv2d(in_channels=in_features, out_channels=in_features, kernel_size=3),
            nn.InstanceNorm2d(in_features),
        )
        return residual_block

    def __upsampling_block(self, in_features: int, out_features: int) -> tuple:
        upsampling_block = (
            nn.ConvTranspose2d(
                in_channels=in_features,
                out_channels=out_features,
                kernel_size=3,
                stride=2,
                padding=1,
                output_padding=1,
            ),
            nn.InstanceNorm2d(out_features),
            nn.ReLU(inplace=True),
        )
        return upsampling_block


class Shadower(nn.Module):
    def __init__(
        self,
        out_channels: int = 3,
        in_channels: int = 3,
        res_blocks=9,
        downsampling_iterations: int = 2,
        upsampling_iterations: int = 2,
    ):
        super(Shadower, self).__init__()

        in_features = in_channels
        out_features = 64

        # initial conv layer
        self.model = nn.Sequential(
            nn.ReflectionPad2d(3),
            # Additional channel is added to in_channels
            # because of the presence of the mask
            nn.Conv2d(in_features := in_features + 1, out_features, kernel_size=7),
            nn.InstanceNorm2d(out_features),
            nn.ReLU(inplace=True),
        )

        in_features = out_features
        out_features = in_features * 2

        downsampling_block = (
            nn.Conv2d(in_channels, out_channels, 3, stride=2, padding=1),
            nn.InstanceNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

        for num in range(downsampling_iterations):
            self.model, *_ = map(
                self.model.append, self.__downsampling_block(in_features, out_features)
            )
            in_features = out_features
            out_features = in_features * 2

        # residual blocks
        residual_block = (
            nn.ReflectionPad2d(1),
            nn.Conv2d(in_channels, in_channels, kernel_size=3),
            nn.InstanceNorm2d(in_channels),
            nn.ReLU(inplace=True),
            nn.ReflectionPad2d(1),
            nn.Conv2d(in_channels, in_channels, 3),
            nn.InstanceNorm2d(in_channels),
        )
        if res_blocks <= 0:
            raise Exception(
                f"res_blocks number should be positive number (it's: {res_blocks})"
            )

        # in_features = out_features
        for _ in range(res_blocks):
            self.model, *_ = map(
                self.model.append, self.__residual_block(in_features, out_features)
            )

        print(
            f"in_features: {in_features}, out_features: {out_features}\tafter residual\n "
        )

        # upsampling
        out_features = in_features // 2
        upsampling_block = (
            nn.ConvTranspose2d(in_channels, out_channels, 3, stride=2, padding=1),
            nn.InstanceNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )
        for _ in range(upsampling_iterations):
            self.model, *_ = map(
                self.model.append, self.__upsampling_block(in_features, out_features)
            )
            in_features = out_features
            out_features = in_features // 2

            print(
                f"in_features: {in_features}, out_features: {out_features}\tafter upsampling num: {num+1}\n "
            )

        # in_channels = out_channels
        # out_channels = in_channels // 2

        # output layer
        self.model.append(nn.ReflectionPad2d(3))
        self.model.append(nn.Conv2d(64, out_channels, 7))

        # print("------------------------------------")
        # print(self.model)
        # print("SHADOWER")

        # print("------------------------------------")
        # raise

    def forward(self, x: Any, mask):
        """
        Forward method \n
        returns \n
        (self.model(torch.cat((x, mask), 1)) + x).tanh()"""

        print(x.size(), mask.size(), sep="\n")
        return (self.model(torch.cat((x, mask), 1)) + x).tanh()
        # return (self.model(torch.cat((x, mask), 1))).tanh()

    def __residual_block(self, in_features: int, out_features: int) -> tuple:
        residual_block = (
            nn.ReflectionPad2d(1),
            nn.Conv2d(in_features, in_features, kernel_size=3),
            nn.InstanceNorm2d(in_features),
            nn.ReLU(inplace=True),
            nn.ReflectionPad2d(1),
            nn.Conv2d(in_features, in_features, 3),
            nn.InstanceNorm2d(in_features),
        )
        return residual_block

    def __upsampling_block(self, in_features: int, out_features: int) -> tuple:
        upsampling_block = (
            nn.ConvTranspose2d(in_features, out_features, 3, stride=2, padding=1),
            nn.InstanceNorm2d(out_features),
            nn.ReLU(inplace=True),
        )
        return upsampling_block

    def __downsampling_block(self, in_features: int, out_features: int) -> tuple:
        downsampling_block = (
            nn.Conv2d(in_features, out_features, 3, stride=2, padding=1),
            nn.InstanceNorm2d(out_features),
            nn.ReLU(inplace=True),
        )
        return downsampling_block


# tobe removed


class Generator_S2F(nn.Module):
    def __init__(self, in_channels, out_channels, n_residual_blocks=9):
        super(Generator_S2F, self).__init__()
        input_nc = in_channels
        output_nc = out_channels

        # Initial convolution block
        model = [
            nn.ReflectionPad2d(3),
            nn.Conv2d(input_nc, 64, 7),
            nn.InstanceNorm2d(64),
            nn.ReLU(inplace=True),
        ]

        # Downsampling
        in_features = 64
        out_features = in_features * 2
        for _ in range(2):
            model += [
                nn.Conv2d(in_features, out_features, 3, stride=2, padding=1),
                nn.InstanceNorm2d(out_features),
                nn.ReLU(inplace=True),
            ]
            in_features = out_features
            out_features = in_features * 2

        # Residual blocks
        for _ in range(n_residual_blocks):
            model += [ResidualBlock(in_features)]

        # Upsampling
        out_features = in_features // 2
        for _ in range(2):
            model += [
                nn.ConvTranspose2d(
                    in_features, out_features, 3, stride=2, padding=1, output_padding=1
                ),
                nn.InstanceNorm2d(out_features),
                nn.ReLU(inplace=True),
            ]
            in_features = out_features
            out_features = in_features // 2

        # Output layer
        model += [nn.ReflectionPad2d(3), nn.Conv2d(64, output_nc, 7)]
        # nn.Tanh() ]

        self.model = nn.Sequential(*model)

    def forward(self, x):
        return (self.model(x) + x).tanh()  # (min=-1, max=1) #just learn a residual


class Generator_F2S(nn.Module):
    def __init__(self, in_channels, out_channels, n_residual_blocks=9):
        super(Generator_F2S, self).__init__()
        input_nc = in_channels
        output_nc = out_channels
        # Initial convolution block
        model = [
            nn.ReflectionPad2d(3),
            nn.Conv2d(input_nc + 1, 64, 7),  # + mask
            nn.InstanceNorm2d(64),
            nn.ReLU(inplace=True),
        ]

        # Downsampling
        in_features = 64
        out_features = in_features * 2
        for _ in range(2):
            model += [
                nn.Conv2d(in_features, out_features, 3, stride=2, padding=1),
                nn.InstanceNorm2d(out_features),
                nn.ReLU(inplace=True),
            ]
            in_features = out_features
            out_features = in_features * 2

        # Residual blocks
        for _ in range(n_residual_blocks):
            model += [ResidualBlock(in_features)]

        # Upsampling
        out_features = in_features // 2
        for _ in range(2):
            model += [
                nn.ConvTranspose2d(
                    in_features, out_features, 3, stride=2, padding=1, output_padding=1
                ),
                nn.InstanceNorm2d(out_features),
                nn.ReLU(inplace=True),
            ]
            in_features = out_features
            out_features = in_features // 2

        # Output layer
        model += [nn.ReflectionPad2d(3), nn.Conv2d(64, output_nc, 7)]
        # nn.Tanh() ]

        self.model = nn.Sequential(*model)

    def forward(self, x, mask):
        with torch.no_grad():
            output = (self.model(torch.cat((x, mask), 1)) + x).tanh()
        # return (
        #     self.model(torch.cat((x, mask), 1)) + x
        # ).tanh()  # (min=-1, max=1) #just learn a residual
        return output


class Discriminator(nn.Module):
    def __init__(
        self,
        in_channels: int,
        layers_number: int = 3,
    ) -> None:
        super(Discriminator, self).__init__()

        # print("_______________________________")
        # print("DISCRIMINATOR")

        self.model = nn.Sequential(
            nn.Conv2d(
                in_channels, out_features := 64, kernel_size=4, stride=2, padding=1
            ),
            nn.LeakyReLU(0.2, inplace=True),
        )
        # temp
        out_channels = 64

        in_features = out_features
        out_features = in_features * 2
        # print(f"in_features:\t{in_features}\tout_features\t{out_features}\tafter init")
        downsampling_block = (
            nn.Conv2d(
                in_channels := out_channels,
                out_channels := out_channels * 2,
                kernel_size=4,
                stride=2,
                padding=1,
            ),
            nn.InstanceNorm2d(out_channels),  # try nn.BatchNorm2d()
            nn.LeakyReLU(0.2, inplace=True),
        )
        if layers_number <= 0:
            raise Exception("layers_number should be greater than 0")

        for num in range(layers_number):
            # print(f"ALOHA {num} of {layers_number}")
            self.model, *_ = map(
                self.model.append, self.__downsampling_block(in_features, out_features)
            )
            # print(
            #     f"in_features:\t{in_features}\tout_features\t{out_features}\tlayer num:\t{num+1}"
            # )
            in_features = out_features
            out_features *= 2
        # classification layer
        self.model.append(
            nn.Conv2d(
                in_channels=512,
                out_channels=1,
                kernel_size=4,
                stride=2,
                padding=1,
            )
        )
        # print(f"in_features:\t{512}\tout_features\t{1}\tlast layer ")
        # print("_______________________________")

    def forward(self, x: Any):
        # with torch.no_grad():
        #     x = self.model(x)
        #     output = F.avg_pool2d(x, x.size()[2:]).view(x.size()[0], -1)
        # return output
        x = self.model(x)
        return F.avg_pool2d(x, x.size()[2:]).view(
            x.size()[0], -1
        )  # consider other forward function

    def __downsampling_block(self, in_features: int, out_features: int) -> tuple:

        downsampling_block = (
            nn.Conv2d(
                in_channels=in_features,
                out_channels=out_features,
                kernel_size=4,
                stride=2,
                padding=1,
            ),
            nn.InstanceNorm2d(out_features),  # try nn.BatchNorm2d()
            nn.LeakyReLU(0.2, inplace=True),
        )
        return downsampling_block
