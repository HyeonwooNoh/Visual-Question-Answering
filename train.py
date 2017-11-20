import shutil
import time
from tensorboardX import SummaryWriter
import torch
from torch.autograd import Variable
from IPython.core.debugger import Pdb


def train(model, train_loader, criterion, optimizer, use_gpu=False):
    model.train()  # Set model to training mode
    running_loss = 0.0
    running_corrects = 0
    example_count = 0
    step = 0
    # Iterate over data.
    for questions, images, answers in train_loader:
        # print(all_lengths)
        questions, images, answers = Variable(questions).transpose(0, 1), Variable(images), Variable(answers)
        if use_gpu:
            questions, images, answers = questions.cuda(), images.cuda(), answers.cuda()

        # zero grad
        optimizer.zero_grad()
        ans_scores = model(images, questions)
        _, preds = torch.max(ans_scores, 1)
        loss = criterion(ans_scores, answers)

        # backward + optimize
        loss.backward()
        optimizer.step()

        # statistics
        running_loss += loss.data[0]
        running_corrects += torch.sum((preds == answers).data)
        example_count += answers.size(0)
        step += 1
        if step % 100 == 0:
            print('running loss: {}, running_corrects: {}, example_count: {}, acc: {}'.format(running_loss / example_count, running_corrects, example_count, (float(running_corrects) / example_count) * 100))
        # if step * batch_size == 40000:
        #     break
    loss = running_loss / example_count
    acc = (running_corrects / example_count) * 100
    print('Train Loss: {:.4f} Acc: {:2.3f} ({}/{})'.format(loss, acc, running_corrects, example_count))
    return loss, acc


def validate(model, dataloader, criterion, use_gpu=False):
    model.eval()  # Set model to evaluate mode
    running_loss = 0.0
    running_corrects = 0
    example_count = 0
    # Iterate over data.
    for questions, images, answers in dataloader:
        # print(all_lengths)
        questions, images, answers = Variable(questions).transpose(0, 1), Variable(images), Variable(answers)
        if use_gpu:
            questions, images, answers = questions.cuda(), images.cuda(), answers.cuda()

        # zero grad
        ans_scores = model(images, questions)
        _, preds = torch.max(ans_scores, 1)
        loss = criterion(ans_scores, answers)

        # statistics
        running_loss += loss.data[0]
        running_corrects += torch.sum((preds == answers).data)
        example_count += answers.size(0)
    loss = running_loss / example_count
    acc = (running_corrects / example_count) * 100
    print('Validation Loss: {:.4f} Acc: {:2.3f} ({}/{})'.format(loss, acc, running_corrects, example_count))
    return loss, acc


def train_model(model, data_loaders, criterion, optimizer, scheduler, save_dir, num_epochs=25, use_gpu=False):
    print('Training Model with use_gpu={}...'.format(use_gpu))
    since = time.time()

    best_model_wts = model.state_dict()
    best_acc = 0.0
    writer = SummaryWriter(save_dir)
    for epoch in range(num_epochs):
        print('Epoch {}/{}'.format(epoch, num_epochs - 1))
        print('-' * 10)
        train_begin = time.time()
        train_loss, train_acc = train(model, data_loaders['train'], criterion, optimizer, use_gpu)
        train_time = time.time() - train_begin
        print('Epoch Train Time: {:.0f}m {:.0f}s'.format(train_time // 60, train_time % 60))
        writer.add_scalar('Train Loss', train_loss, epoch)
        writer.add_scalar('Train Accuracy', train_acc, epoch)

        validation_begin = time.time()
        val_loss, val_acc = validate(model, data_loaders['val'], criterion, use_gpu)
        validation_time = time.time() - validation_begin
        print('Epoch Validation Time: {:.0f}m {:.0f}s'.format(validation_time // 60, validation_time % 60))
        writer.add_scalar('Validation Loss', val_loss, epoch)
        writer.add_scalar('Validation Accuracy', val_acc, epoch)

        # deep copy the model
        is_best = val_acc > best_acc
        if is_best:
            best_acc = val_acc
            best_model_wts = model.state_dict()

        save_checkpoint(save_dir, {
            'epoch': epoch,
            'best_acc': best_acc,
            'state_dict': model.state_dict(),
            # 'optimizer': optimizer.state_dict(),
        }, is_best)

        scheduler.step()

    time_elapsed = time.time() - since
    print('Training complete in {:.0f}m {:.0f}s'.format(
        time_elapsed // 60, time_elapsed % 60))
    print('Best val Acc: {:4f}'.format(best_acc))
    # load best model weights
    model.load_state_dict(best_model_wts)

    # export scalar data to JSON for external processing
    writer.export_scalars_to_json(save_dir + "/all_scalars.json")
    writer.close()

    return model


def save_checkpoint(save_dir, state, is_best):
    savepath = save_dir + '/' + 'checkpoint.pth.tar'
    torch.save(state, savepath)
    if is_best:
        shutil.copyfile(savepath, save_dir + '/' + 'model_best.pth.tar')


def test_model(model, dataloader, use_gpu=False):
    model.eval()  # Set model to evaluate mode
    running_corrects = 0
    example_count = 0
    test_begin = time.time()
    # Iterate over data.
    for questions, images, answers in dataloader:
        # print(all_lengths)
        questions, images, answers = Variable(questions).transpose(0, 1), Variable(images), Variable(answers)
        if use_gpu:
            questions, images, answers = questions.cuda(), images.cuda(), answers.cuda()

        # zero grad
        ans_scores = model(images, questions)
        _, preds = torch.max(ans_scores, 1)

        # statistics
        running_corrects += torch.sum((preds == answers).data)
        example_count += answers.size(0)
    acc = (running_corrects / example_count) * 100
    print('Test Acc: {:2.3f} ({}/{})'.format(acc, running_corrects, example_count))
    test_time = time.time() - test_begin
    print('Test Time: {:.0f}m {:.0f}s'.format(test_time // 60, test_time % 60))
    return acc
