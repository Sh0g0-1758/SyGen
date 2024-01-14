# After understanding the paper on GANs by Ian J. Goodfellow, Here is the implementation of the same.

# Vanilla GAN architecture using Linear neural network layers

# While Training, the D and G need to train simultaneously. We can implement this using Threads but that gets complicated. So we will try a different approach.

# Training the Discriminator : Get the real data and labels. Do a forward pass into the DNN to get the real output. Use it to calculate the D-Loss and backpropagate it. Use the noice vector, generate fake data and labels using the generator and do a forward pass through the Discriminator to get the fake output. Use it to calculate the D-Loss and backpropagate it. Add the two losses and update the weights of the Discriminator.

# Training the Generator : Use the noice vector, generate fake data and labels using the generator and do a forward pass through the Discriminator to get the fake output. Use it to calculate the G-Loss and backpropagate it. Update the weights of the Generator.

# Importing the libraries
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torch.optim as optim
import torchvision.datasets as datasets
import imageio
import numpy as np
import matplotlib
from torchvision.utils import make_grid, save_image  # to save PyTorch tensor images
from torch.utils.data import DataLoader
from matplotlib import pyplot as plt
from tqdm import tqdm
matplotlib.style.use('ggplot')

# ANSI escape code for colors


class colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'

### Some Utility Functions ###
# to create real labels (1s)


def label_real(size):
    data = torch.ones(size, 1)
    return data.to(device)
# to create fake labels (0s)


def label_fake(size):
    data = torch.zeros(size, 1)
    return data.to(device)
# function to create the noise vector


def create_noise(sample_size, nz):
    return torch.randn(sample_size, nz).to(device)
# to save the images generated by the generator


def save_generator_image(image, path):
    save_image(image, path)


# learning parameters
# Since the MNIST data-set is small, we can use much greater batch size also.
batch_size = 512
# number of training Epochs. After 200 epochs, the images will be clear. Less epochs will produce random noise.
epochs = 200
sample_size = 64  # fixed sample size
nz = 128  # latent / noise vector size
k = 1  # number of steps to apply to the discriminator
# Citing Algorithm 1 mentioned in the paper as the reason :
# Algorithm 1 Minibatch stochastic gradient descent training of generative adversarial nets. The number of
# steps to apply to the discriminator, k, is a hyperparameter. We used k = 1, the least expensive option, in our
# experiments.
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


# Preparing the dataset
transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,)),
])  # This converts the images to tensors and normalizes them as well

# To convert the images into PIL format, will be useful in changing the images in gif format.
to_pil_image = transforms.ToPILImage()

train_data = datasets.MNIST(
    root='dataset/vanilla_gan/',
    train=True,
    download=True,
    transform=transform
)
# loading the data in batches
train_loader = DataLoader(train_data, batch_size=batch_size, shuffle=True)

# Generator Network , a simple Feed Forward Neural Network


class Generator(nn.Module):
    def __init__(self, nz):
        super(Generator, self).__init__()
        self.nz = nz
        self.main = nn.Sequential(
            nn.Linear(self.nz, 256),
            nn.LeakyReLU(0.2),
            nn.Linear(256, 512),
            nn.LeakyReLU(0.2),
            nn.Linear(512, 1024),
            nn.LeakyReLU(0.2),
            nn.Linear(1024, 784),
            nn.Tanh(),
        )  # LeakyRELu [max(0.1x,x)] introduce non-linearities to capture complex patterns while Tanh ensures that the generator's output is within a suitable range for image data

    def forward(self, x):
        # -1 is given to infer the batch size automatically. 1 for grayscale, and the 28*28 is the size of the image.
        return self.main(x).view(-1, 1, 28, 28)

# Discriminator Network , a simple Feed Forward Neural Network


class Discriminator(nn.Module):
    def __init__(self):
        super(Discriminator, self).__init__()
        self.n_input = 784
        self.main = nn.Sequential(
            nn.Linear(self.n_input, 1024),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            nn.Linear(1024, 512),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            nn.Linear(256, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        x = x.view(-1, 784)
        return self.main(x)


# Creating the Generator and Discriminator objects
generator = Generator(nz).to(device)
discriminator = Discriminator().to(device)
print(colors.BLUE + '##### GENERATOR #####' + colors.RESET)
print(colors.CYAN + str(generator) + colors.RESET)
print(colors.BLUE + '######################' + colors.RESET)
print(colors.BLUE + '\n##### DISCRIMINATOR #####' + colors.RESET)
print(colors.CYAN + str(discriminator) + colors.RESET)
print(colors.BLUE + '######################' + colors.RESET)

# optimizers
optim_g = optim.Adam(generator.parameters(), lr=0.0002)
optim_d = optim.Adam(discriminator.parameters(), lr=0.0002)

# loss function
criterion = nn.BCELoss()  # Binary Cross Entropy Loss

# Lists to store epoch-wise Loss values and images generated
losses_g = []  # to store generator loss after each epoch
losses_d = []  # to store discriminator loss after each epoch
images = []  # to store images generatd by the generator

# function to train the discriminator network


def train_discriminator(optimizer, data_real, data_fake):
    b_size = data_real.size(0)
    real_label = label_real(b_size)  # real label is 1
    fake_label = label_fake(b_size)  # fake label is 0
    optimizer.zero_grad()  # so as to clear the gradients from previous training iteration
    # forward pass through the discriminator network
    output_real = discriminator(data_real)
    loss_real = criterion(output_real, real_label)  # calculating the loss
    # forward pass through the discriminator network
    output_fake = discriminator(data_fake)
    loss_fake = criterion(output_fake, fake_label)  # calculating the loss
    loss_real.backward()  # backpropagating the gradients
    loss_fake.backward()  # backpropagating the gradients
    optimizer.step()  # updating the weights
    return loss_real + loss_fake  # returning the total loss

# function to train the generator network


def train_generator(optimizer, data_fake):
    b_size = data_fake.size(0)  # getting the batch size
    real_label = label_real(b_size)  # real label is 1
    optimizer.zero_grad()  # so as to clear the gradients from previous training iteration
    # forward pass through the discriminator network
    output = discriminator(data_fake)
    loss = criterion(output, real_label)  # calculating the loss
    loss.backward()  # backpropagating the gradients
    optimizer.step()  # updating the weights
    return loss  # returning the loss


# create the noise vector
noise = create_noise(sample_size, nz)

# Switching both networks to training mode
generator.train()
discriminator.train()

# Training the Vanilla GAN
for epoch in range(epochs):
    loss_g = 0.0
    loss_d = 0.0
    for bi, data in tqdm(enumerate(train_loader), total=int(len(train_data)/train_loader.batch_size)):
        image, _ = data
        image = image.to(device)
        b_size = len(image)
        # run the discriminator for k number of steps
        for step in range(k):
            data_fake = generator(create_noise(b_size, nz)).detach()
            data_real = image
            # train the discriminator network
            loss_d += train_discriminator(optim_d, data_real, data_fake)
        data_fake = generator(create_noise(b_size, nz))
        # train the generator network
        loss_g += train_generator(optim_g, data_fake)
    # create the final fake image for the epoch
    generated_img = generator(noise).cpu().detach()
    # make the images as grid
    generated_img = make_grid(generated_img)
    # save the generated torch tensor models to disk
    save_generator_image(generated_img, f"./outputs/gen_img_{epoch}.png")
    images.append(generated_img)
    epoch_loss_g = loss_g / bi  # total generator loss for the epoch
    epoch_loss_d = loss_d / bi  # total discriminator loss for the epoch
    losses_g.append(epoch_loss_g)
    losses_d.append(epoch_loss_d)

    print(colors.BLUE + f"Epoch {epoch} of {epochs}" + colors.RESET)
    print(colors.CYAN +
          f"Generator loss: {epoch_loss_g:.8f}, Discriminator loss: {epoch_loss_d:.8f}" + colors.RESET)

# save the model parameters for inference
print(colors.GREEN + 'DONE TRAINING' + colors.RESET)
torch.save(generator.state_dict(), './results/generator.pth')

# save the generated images as GIF file
imgs = [np.array(to_pil_image(img)) for img in images]
imageio.mimsave('./results/generator_images.gif', imgs)

# plot and save the generator and discriminator loss
plt.figure()
plt.plot([loss.item() for loss in losses_g], label='Generator loss')
plt.plot([loss.item() for loss in losses_d], label='Discriminator Loss')
plt.legend()
plt.savefig('./results/loss.png')
plt.show()
